from flask_pymongo import PyMongo
from datetime import datetime
from bson import ObjectId

class Database:
    def __init__(self, app):
        self.mongo = PyMongo(app)
        self._create_indexes()

    def _create_indexes(self):
        # Create required indexes
        self.mongo.db.users.create_index("email", unique=True)
        self.mongo.db.subscriptions.create_index([("user_id", 1), ("name", 1)])
        self.mongo.db.password_resets.create_index("token", unique=True)
        self.mongo.db.password_resets.create_index("expiry", expireAfterSeconds=3600)

    def create_user(self, username, email, password_hash):
        user_data = {
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "created_at": datetime.utcnow()
        }
        result = self.mongo.db.users.insert_one(user_data)
        return str(result.inserted_id)

    def get_user_by_email(self, email):
        return self.mongo.db.users.find_one({"email": email})

    def get_user_by_id(self, user_id):
        return self.mongo.db.users.find_one({"_id": ObjectId(user_id)})

    def create_subscription(self, user_id, name, amount, category, renewal_date, frequency):
        subscription_data = {
            "user_id": ObjectId(user_id),
            "name": name,
            "amount": float(amount),
            "category": category,
            "renewal_date": renewal_date,
            "frequency": frequency,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        return self.mongo.db.subscriptions.insert_one(subscription_data)

    def get_user_subscriptions(self, user_id):
        return self.mongo.db.subscriptions.find({"user_id": ObjectId(user_id)})

    def delete_subscription(self, subscription_id, user_id):
        return self.mongo.db.subscriptions.delete_one({
            "_id": ObjectId(subscription_id),
            "user_id": ObjectId(user_id)
        })

    def create_password_reset(self, email, token, expiry):
        reset_data = {
            "email": email,
            "token": token,
            "expiry": expiry
        }
        return self.mongo.db.password_resets.insert_one(reset_data)

    def get_password_reset(self, token):
        return self.mongo.db.password_resets.find_one({
            "token": token,
            "expiry": {"$gt": datetime.utcnow()}
        })

    def update_user_password(self, email, password_hash):
        return self.mongo.db.users.update_one(
            {"email": email},
            {"$set": {"password_hash": password_hash}}
        )

    def delete_password_reset(self, token):
        return self.mongo.db.password_resets.delete_one({"token": token})

    def update_user_login(self, user_id):
        """Update user's last login time and login count"""
        # First, ensure the user has a login_count field
        user = self.mongo.db.users.find_one({"_id": ObjectId(user_id)})
        if 'login_count' not in user:
            # Initialize login_count if it doesn't exist
            self.mongo.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"login_count": 0}}
            )

        # Now update the login time and increment the counter
        return self.mongo.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {"last_login": datetime.utcnow()},
                "$inc": {"login_count": 1}
            }
        )

    def invalidate_user_sessions(self, user_id):
        """Invalidate all user sessions"""
        return self.mongo.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"session_valid": False}}
        )