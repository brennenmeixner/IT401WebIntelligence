"""Flask extension objects, created once and shared by the whole app.

They are created here *without* an app and bound later inside
create_app() with init_app(). This avoids circular imports: models import
`db` from here, and app.py imports both.
"""

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
