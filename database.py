from flask_pymongo import PyMongo
from datetime import datetime
from bson import ObjectId
from dateutil.relativedelta import relativedelta
from pymongo import MongoClient
import os

class Database:
    def __init__(self, app):
        self.client = MongoClient(app.config['MONGO_URI'])
        # Simply use the database name directly
        self.db = self.client.subscription_tracker
        self._create_indexes()

    def _create_indexes(self):
        self.db.users.create_index("email", unique=True)
        self.db.subscriptions.create_index([("user_id", 1), ("name", 1)])
        
    def create_user(self, username, email, password_hash):
        user_data = {
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "created_at": datetime.utcnow()
        }
        result = self.db.users.insert_one(user_data)
        return str(result.inserted_id)

    def get_user_by_email(self, email):
        return self.db.users.find_one({"email": email})

    def get_user_by_id(self, user_id):
        return self.db.users.find_one({"_id": ObjectId(user_id)})

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
        return self.db.subscriptions.insert_one(subscription_data)

    def get_user_subscriptions(self, user_id):
        return self.db.subscriptions.find({"user_id": ObjectId(user_id)})

    def delete_subscription(self, subscription_id, user_id):
        return self.db.subscriptions.delete_one({
            "_id": ObjectId(subscription_id),
            "user_id": ObjectId(user_id)
        })

    def update_user_password(self, email, password_hash):
        return self.db.users.update_one(
            {"email": email},
            {"$set": {"password_hash": password_hash}}
        )

    def update_user_login(self, user_id):
        """Update user's last login time and login count"""
        # First, ensure the user has a login_count field
        user = self.db.users.find_one({"_id": ObjectId(user_id)})
        if 'login_count' not in user:
            # Initialize login_count if it doesn't exist
            self.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"login_count": 0}}
            )

        # Now update the login time and increment the counter
        return self.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {"last_login": datetime.utcnow()},
                "$inc": {"login_count": 1}
            }
        )

    def invalidate_user_sessions(self, user_id):
        """Invalidate all user sessions"""
        return self.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"session_valid": False}}
        )

    def update_subscription_date(self, subscription_id, new_date):
        """Update subscription renewal date"""
        return self.db.subscriptions.update_one(
            {"_id": ObjectId(subscription_id)},
            {
                "$set": {
                    "renewal_date": new_date,
                    "updated_at": datetime.utcnow()
                }
            }
        )