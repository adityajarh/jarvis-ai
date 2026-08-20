from flask import request, jsonify, session
from chat import chat_bp
from models import db, Conversation, Message


@chat_bp.route("/new", methods=["POST"])
def new_conversation():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not logged in."})

    conversation = Conversation(user_id=session["user_id"], title="New chat")
    db.session.add(conversation)
    db.session.commit()

    return jsonify({
        "success": True,
        "conversation_id": conversation.id,
        "title": conversation.title
    })


@chat_bp.route("/list", methods=["GET"])
def list_conversations():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not logged in."})

    conversations = Conversation.query.filter_by(
        user_id=session["user_id"]
    ).order_by(Conversation.created_at.desc()).all()

    return jsonify({
        "success": True,
        "conversations": [
            {"id": c.id, "title": c.title, "created_at": c.created_at.strftime("%d %b %Y %H:%M")}
            for c in conversations
        ]
    })


@chat_bp.route("/<int:conversation_id>/messages", methods=["GET"])
def get_messages(conversation_id):
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not logged in."})

    conversation = Conversation.query.get(conversation_id)

    if not conversation or conversation.user_id != session["user_id"]:
        return jsonify({"success": False, "message": "Conversation not found."})

    messages = Message.query.filter_by(
        conversation_id=conversation_id
    ).order_by(Message.created_at.asc()).all()

    return jsonify({
        "success": True,
        "messages": [
            {"role": m.role, "content": m.content, "created_at": m.created_at.strftime("%H:%M")}
            for m in messages
        ]
    })

from brain import process_command


@chat_bp.route("/<int:conversation_id>/send", methods=["POST"])
def send_message(conversation_id):
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not logged in."})

    conversation = Conversation.query.get(conversation_id)

    if not conversation or conversation.user_id != session["user_id"]:
        return jsonify({"success": False, "message": "Conversation not found."})

    user_message = request.form.get("message", "").strip()

    if not user_message:
        return jsonify({"success": False, "message": "Message is required."})

    username = session.get("user_name", "Friend")

    history = Message.query.filter_by(
        conversation_id=conversation_id
    ).order_by(Message.created_at.asc()).all()

    conversation_history = [
        {"role": "user" if m.role == "user" else "assistant", "content": m.content}
        for m in history
    ]

    ai_response = process_command(user_message, conversation_history, username, session["user_id"])

    user_msg = Message(conversation_id=conversation_id, role="user", content=user_message)
    jarvis_msg = Message(conversation_id=conversation_id, role="jarvis", content=ai_response)
    db.session.add(user_msg)
    db.session.add(jarvis_msg)

    if conversation.title == "New chat":
        conversation.title = user_message[:40]

    db.session.commit()

    return jsonify({
        "success": True,
        "response": ai_response
    })

@chat_bp.route("/<int:conversation_id>/rename", methods=["POST"])
def rename_conversation(conversation_id):
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not logged in."})

    conversation = Conversation.query.get(conversation_id)

    if not conversation or conversation.user_id != session["user_id"]:
        return jsonify({"success": False, "message": "Conversation not found."})

    new_title = request.form.get("title", "").strip()

    if not new_title:
        return jsonify({"success": False, "message": "Title is required."})

    conversation.title = new_title[:40]
    db.session.commit()

    return jsonify({"success": True, "title": conversation.title})

@chat_bp.route("/<int:conversation_id>/delete", methods=["DELETE"])
def delete_conversation(conversation_id):
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not logged in."})

    conversation = Conversation.query.get(conversation_id)

    if not conversation or conversation.user_id != session["user_id"]:
        return jsonify({"success": False, "message": "Conversation not found."})

    Message.query.filter_by(conversation_id=conversation_id).delete()
    db.session.delete(conversation)
    db.session.commit()

    return jsonify({"success": True, "message": "Conversation deleted."})