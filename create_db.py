from application import db
from application import app

with app.test_request_context():
    db.init_app(app)
    db.create_all()
