from app import app, db
from models import User, Note, ResetCode

with app.app_context():
    # Saare notes delete karo
    Note.query.delete()
    # Saare reset codes delete karo
    ResetCode.query.delete()
    # Saare users delete karo
    User.query.delete()
    # Commit karo
    db.session.commit()
    print("✅ All users, notes, and reset codes deleted successfully!")