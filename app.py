from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_talisman import Talisman
from datetime import datetime, timedelta
from models import User, Subscription
from database import Database
from flask_mail import Mail, Message
from secrets import token_urlsafe

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  # Change this in production
app.config['MONGO_URI'] = "mongodb+srv://anindyakanti2020:8me3AfdtPHmtXTbW@cluster0.klcr5.mongodb.net/subscription_tracker?retryWrites=true&w=majority"

# Add this custom filter
@app.template_filter('strftime')
def _jinja2_filter_strftime(date, fmt=None):
    if fmt is None:
        fmt = '%d %b'
    return date.strftime(fmt)

# Initialize extensions
Talisman(app, content_security_policy=None)
db = Database(app)

# Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-gmail@gmail.com'
app.config['MAIL_PASSWORD'] = 'your-16-digit-app-password'
mail = Mail(app)

# Session configuration
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)
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
            if remember:
                session.permanent = True
            
            login_user(user, 
                      remember=remember, 
                      duration=app.config['REMEMBER_COOKIE_DURATION'],  # Changed this line
                      force=True)
            
            db.update_user_login(user.id)
            session['_id'] = token_urlsafe(32)
            
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('dashboard'))
            
        flash('Invalid email or password')
    return render_template('login.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email')
        user_data = db.get_user_by_email(email)
        
        if user_data:
            try:
                reset_token = token_urlsafe(32)
                expiry = datetime.utcnow() + timedelta(hours=1)
                
                db.create_password_reset(email, reset_token, expiry)
                
                reset_url = url_for('reset_password', token=reset_token, _external=True)
                msg = Message('Password Reset Request',
                            sender=app.config['MAIL_USERNAME'],
                            recipients=[email])
                msg.body = f'''To reset your password, visit the following link:
{reset_url}

If you did not make this request, please ignore this email.
'''
                mail.send(msg)
                flash('Reset instructions sent to your email')
                return redirect(url_for('login'))
            except Exception as e:
                flash('Error sending reset email. Please try again.')
                print(f"Password reset error: {e}")
        else:
            flash('Email address not found')
    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    reset_data = db.get_password_reset(token)
    
    if not reset_data:
        flash('Invalid or expired reset link')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            
            if password != confirm_password:
                flash('Passwords do not match')
                return render_template('reset_password.html')
                
            user = User.create(None, reset_data['email'], password)
            db.update_user_password(reset_data['email'], user.password_hash)
            db.delete_password_reset(token)
            
            flash('Your password has been updated')
            return redirect(url_for('login'))
        except Exception as e:
            flash('Error resetting password. Please try again.')
            print(f"Password update error: {e}")
            
    return render_template('reset_password.html')

# Protected routes - require login
@app.route('/dashboard')
@login_required
def dashboard():
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

if __name__ == '__main__':
    app.run(debug=True)
