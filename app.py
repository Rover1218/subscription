from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_talisman import Talisman
from datetime import datetime, timedelta
from models import User, Subscription
from database import Database
from flask_mail import Mail, Message
from secrets import token_urlsafe
from dotenv import load_dotenv
import os
from dateutil.relativedelta import relativedelta  # Add this import

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')  # Change this in production
app.config['MONGO_URI'] = os.getenv('MONGO_URI')

# Add this custom filter
@app.template_filter('strftime')
def _jinja2_filter_strftime(date, fmt=None):
    if fmt is None:
        fmt = '%d %b'
    return date.strftime(fmt)

# Initialize extensions
Talisman(app, content_security_policy=None)
db = Database(app)

# Session configuration
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)  # Default session lifetime
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)  # Remember me duration
app.config['REMEMBER_COOKIE_SECURE'] = True
app.config['REMEMBER_COOKIE_HTTPONLY'] = True

# Configure session protection
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'error'
login_manager.session_protection = 'strong'

@login_manager.user_loader
def load_user(user_id):
    user_data = db.get_user_by_id(user_id)
    return User.from_db_dict(user_data) if user_data else None

# Public routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if db.get_user_by_email(email):
            flash('Email already registered')
            return redirect(url_for('register'))
        
        try:
            user = User.create(username, email, password)
            user_id = db.create_user(user.username, user.email, user.password_hash)
            flash('Registration successful! Please login.')
            return redirect(url_for('login'))
        except Exception as e:
            flash('Registration failed. Please try again.')
            print(f"Registration error: {e}")
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember', False) == 'on'
        
        user_data = db.get_user_by_email(email)
        user = User.from_db_dict(user_data) if user_data else None
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            session.permanent = True  # Make session permanent by default
            session['_id'] = token_urlsafe(32)
            db.update_user_login(user.id)
            
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('dashboard'))
            
        flash('Invalid email or password')
    return render_template('login.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    return redirect(url_for('login'))

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    return redirect(url_for('login'))

# Protected routes - require login
@app.route('/dashboard')
@login_required
def dashboard():
    # Update subscription dates before displaying
    update_subscription_dates()
    subscriptions = list(db.get_user_subscriptions(current_user.id))
    return render_template('dashboard.html', 
                         subscriptions=subscriptions,
                         now=datetime.utcnow(),
                         timedelta=timedelta)

@app.route('/add_subscription', methods=['GET', 'POST'])
@login_required
def add_subscription():
    if request.method == 'POST':
        try:
            db.create_subscription(
                user_id=current_user.id,
                name=request.form['name'],
                amount=request.form['amount'],
                category=request.form['category'],
                renewal_date=datetime.strptime(request.form['renewal_date'], "%Y-%m-%d"),
                frequency=request.form['frequency']
            )
            flash('Subscription added successfully!')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash('Error adding subscription. Please try again.')
            print(f"Subscription error: {e}")
    return render_template('add_subscription.html')

@app.route('/delete_subscription/<subscription_id>', methods=['POST'])
@login_required
def delete_subscription(subscription_id):
    try:
        db.delete_subscription(subscription_id, current_user.id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/logout')
@login_required
def logout():
    # Clear session and remember me token
    session.clear()
    logout_user()
    return redirect(url_for('home'))

# API routes
@app.route('/api/reminders')
@login_required
def get_reminders():
    try:
        subscriptions = list(db.get_user_subscriptions(current_user.id))
        reminders = [
            sub for sub in subscriptions 
            if sub['renewal_date'] - datetime.utcnow() <= timedelta(days=7)
        ]
        return jsonify({'reminders': reminders})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Global before_request handler
@app.before_request
def before_request():
    if not current_user.is_authenticated:
        # List of routes that don't require authentication
        public_routes = ['home', 'login', 'register', 
                        'forgot_password', 'reset_password', 
                        'static']
        
        # Check if the requested endpoint requires authentication
        if request.endpoint and request.endpoint not in public_routes:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login', next=request.url))
    
    # For authenticated users, verify session
    elif current_user.is_authenticated:
        session.modified = True
        if '_id' not in session:
            logout_user()
            return redirect(url_for('login'))

# Error handlers
@app.errorhandler(401)
def unauthorized(error):
    flash('Please log in to access this page.', 'error')
    return redirect(url_for('login'))

@app.errorhandler(404)
def page_not_found(error):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    return render_template('404.html'), 404

# Add new function to update subscription dates
def update_subscription_dates():
    """Update renewal dates for passed subscriptions"""
    now = datetime.utcnow()
    subscriptions = db.get_user_subscriptions(current_user.id)
    
    for sub in subscriptions:
        if sub['renewal_date'] < now:
            # Calculate next renewal date based on frequency
            frequency = sub['frequency']
            old_date = sub['renewal_date']
            
            if frequency == 'Monthly':
                new_date = old_date + relativedelta(months=1)
            elif frequency == 'Quarterly':
                new_date = old_date + relativedelta(months=3)
            elif frequency == 'Semi-Annual':
                new_date = old_date + relativedelta(months=6)
            elif frequency == 'Annual':
                new_date = old_date + relativedelta(years=1)
            
            # Update subscription with new renewal date
            db.update_subscription_date(sub['_id'], new_date)

if __name__ == '__main__':
    app.run(debug=True)

# Add this block at the end of the file to make it compatible with Vercel
app = Flask(__name__)
# ...existing code...
