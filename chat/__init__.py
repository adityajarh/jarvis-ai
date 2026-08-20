from flask import Blueprint

chat_bp = Blueprint(
    'chat',
    __name__,
    static_folder='static',
    template_folder='templates'
)

from chat import routes