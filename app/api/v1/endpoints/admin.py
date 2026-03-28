"""Admin endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.models.alias import Alias
from app.models.incoming_message import IncomingMessage
from app.models.parsing_rule import ParsingRule
from app.models.verification_session import VerificationSession
from app.schemas.alias import AliasOut
from app.schemas.message import IncomingMessageOut
from app.schemas.parsing_rule import ParsingRuleCreate, ParsingRuleOut, ParsingRuleUpdate
from app.schemas.session import SessionStatusResponse
from app.models.verification_session import SessionStatus
from app.services.cleanup_service import run_cleanup
from app.workers import gmail_worker
from app.integrations.gmail.watcher import renew_watch
from app.core.config import get_settings

router = APIRouter(dependencies=[Depends(require_admin)])


# ── Parsing Rules ────────────────────────────────────────────────────────────

@router.post("/parsing-rules", response_model=ParsingRuleOut, status_code=status.HTTP_201_CREATED)
async def create_parsing_rule(
    body: ParsingRuleCreate, db: AsyncSession = Depends(get_db)
) -> ParsingRuleOut:
    rule = ParsingRule(**body.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return ParsingRuleOut.model_validate(rule)


@router.get("/parsing-rules", response_model=list[ParsingRuleOut])
async def list_parsing_rules(db: AsyncSession = Depends(get_db)) -> list[ParsingRuleOut]:
    rules = (await db.scalars(select(ParsingRule).order_by(ParsingRule.priority))).all()
    return [ParsingRuleOut.model_validate(r) for r in rules]


@router.patch("/parsing-rules/{rule_id}", response_model=ParsingRuleOut)
async def update_parsing_rule(
    rule_id: int, body: ParsingRuleUpdate, db: AsyncSession = Depends(get_db)
) -> ParsingRuleOut:
    rule = await db.get(ParsingRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    await db.commit()
    await db.refresh(rule)
    return ParsingRuleOut.model_validate(rule)


# ── Gmail ────────────────────────────────────────────────────────────────────

@router.post("/gmail/sync-now")
async def trigger_gmail_sync() -> dict:
    count = await gmail_worker.trigger_sync()
    return {"processed": count}


@router.post("/watch/renew")
async def renew_gmail_watch() -> dict:
    settings = get_settings()
    topic = getattr(settings, "gmail_pubsub_topic", "projects/MY_PROJECT/topics/gmail-push")
    history_id = await renew_watch(topic)
    return {"history_id": history_id}


# ── Sessions ─────────────────────────────────────────────────────────────────

@router.get("/sessions", response_model=list[SessionStatusResponse])
async def list_sessions(
    skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)
) -> list[SessionStatusResponse]:
    sessions = (
        await db.scalars(
            select(VerificationSession).offset(skip).limit(limit).order_by(
                VerificationSession.created_at.desc()
            )
        )
    ).all()
    return [
        SessionStatusResponse(
            session_id=s.public_id,
            status=s.status,
            alias=s.alias_address,
            expires_at=s.expires_at,
            last_checked_at=s.last_checked_at,
            code_found=s.extracted_code is not None,
            completed=s.status == SessionStatus.extracted,
        )
        for s in sessions
    ]


# ── Messages ─────────────────────────────────────────────────────────────────

@router.get("/messages", response_model=list[IncomingMessageOut])
async def list_messages(
    skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)
) -> list[IncomingMessageOut]:
    msgs = (
        await db.scalars(
            select(IncomingMessage).offset(skip).limit(limit).order_by(
                IncomingMessage.created_at.desc()
            )
        )
    ).all()
    return [IncomingMessageOut.model_validate(m) for m in msgs]


# ── Aliases ───────────────────────────────────────────────────────────────────

@router.get("/aliases", response_model=list[AliasOut])
async def list_aliases(
    skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)
) -> list[AliasOut]:
    aliases = (
        await db.scalars(
            select(Alias).offset(skip).limit(limit).order_by(Alias.created_at.desc())
        )
    ).all()
    return [AliasOut.model_validate(a) for a in aliases]


# ── Cleanup ───────────────────────────────────────────────────────────────────

@router.post("/cleanup")
async def run_cleanup_now(db: AsyncSession = Depends(get_db)) -> dict:
    return await run_cleanup(db)
