from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin):
    def __init__(self, id, username, email, password_hash, created_at=None):
        self.id = str(id)
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.created_at = created_at or datetime.utcnow()

    @staticmethod
    def create(username, email, password):
        return User(
            id=None,
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return str(self.id)

    @staticmethod
    def from_db_dict(user_dict):
        if not user_dict:
            return None
        return User(
            id=user_dict['_id'],
            username=user_dict['username'],
            email=user_dict['email'],
            password_hash=user_dict['password_hash'],
            created_at=user_dict.get('created_at')
        )

class Subscription:
    def __init__(self, id, user_id, name, amount, category, renewal_date, frequency):
        self.id = str(id)
        self.user_id = str(user_id)
        self.name = name
        self.amount = float(amount)
        self.category = category
        self.renewal_date = renewal_date
        self.frequency = frequency

    @staticmethod
    def from_db_dict(sub_dict):
        if not sub_dict:
            return None
        return Subscription(
            id=sub_dict['_id'],
            user_id=sub_dict['user_id'],
            name=sub_dict['name'],
            amount=sub_dict['amount'],
            category=sub_dict['category'],
            renewal_date=sub_dict['renewal_date'],
            frequency=sub_dict['frequency']
        )