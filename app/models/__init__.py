"""Models package — import all models so Alembic can discover them."""
from app.models.alias import Alias, AliasStatus  # noqa: F401
from app.models.verification_session import VerificationSession, SessionStatus  # noqa: F401
from app.models.incoming_message import IncomingMessage  # noqa: F401
from app.models.parsing_rule import ParsingRule  # noqa: F401
