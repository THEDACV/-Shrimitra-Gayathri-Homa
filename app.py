from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
import sqlite3
import random
import string
import os
from datetime import datetime
import hashlib

app = Flask(__name__)
app.secret_key = 'gayathri-homa-secret-key-2024-shrimitra-networks'
CORS(app)

# Admin credentials
ADMIN_PASSWORD = "shrimitranet"  # Admin password

# Database setup
def init_db():
    conn = sqlite3.connect('gayathri_homa.db')
    cursor = conn.cursor()
    
    # User Registration table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_registration (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            members_count INTEGER NOT NULL,
            registration_id TEXT UNIQUE NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Homa Kunda table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS homa_kunda (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kunda_number INTEGER UNIQUE NOT NULL,
            status TEXT DEFAULT 'available',
            booked_by_id INTEGER,
            FOREIGN KEY (booked_by_id) REFERENCES user_registration (id)
        )
    ''')
    
    # Booking table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS booking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            kunda_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            booking_id TEXT UNIQUE NOT NULL,
            booked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            approved_at DATETIME,
            admin_notes TEXT,
            FOREIGN KEY (user_id) REFERENCES user_registration (id),
            FOREIGN KEY (kunda_id) REFERENCES homa_kunda (id),
            UNIQUE(user_id, kunda_id)
        )
    ''')
    
    # Admin table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Initialize kundas if not exists
    cursor.execute('SELECT COUNT(*) FROM homa_kunda')
    count = cursor.fetchone()[0]
    if count == 0:
        for i in range(1, 101):
            cursor.execute(
                'INSERT INTO homa_kunda (kunda_number, status) VALUES (?, ?)',
                (i, 'available')
            )
        print("✅ 100 kundas initialized successfully!")
    
    # Initialize admin user if not exists
    cursor.execute('SELECT COUNT(*) FROM admin_users WHERE username = ?', ('admin',))
    if cursor.fetchone()[0] == 0:
        password_hash = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()
        cursor.execute(
            'INSERT INTO admin_users (username, password_hash) VALUES (?, ?)',
            ('admin', password_hash)
        )
        print("✅ Admin user initialized successfully!")
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")

# Utility functions
def generate_registration_id():
    prefix = "GH"
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"{prefix}{random_chars}"

def generate_booking_id():
    prefix = "BK"
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"{prefix}{random_chars}"

def get_db_connection():
    conn = sqlite3.connect('gayathri_homa.db')
    conn.row_factory = sqlite3.Row
    return conn

def is_admin_logged_in():
    return session.get('admin_logged_in', False)

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/admin')
def admin_login_page():
    if is_admin_logged_in():
        return redirect(url_for('admin_dashboard'))
    return render_template('index.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not is_admin_logged_in():
        return redirect(url_for('admin_login_page'))
    return render_template('index.html')

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return jsonify({
                'success': False,
                'error': 'Username and password are required'
            }), 400
        
        # Check password (any username with correct password works)
        if password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session['admin_username'] = username
            print(f"✅ Admin login successful: {username}")
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'username': username
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid password'
            }), 401
            
    except Exception as e:
        print(f"❌ Admin login error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Login failed'
        }), 500

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    session.clear()
    return jsonify({
        'success': True,
        'message': 'Logout successful'
    })

@app.route('/api/admin/stats', methods=['GET'])
def admin_stats():
    if not is_admin_logged_in():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Total registrations
        cursor.execute('SELECT COUNT(*) FROM user_registration')
        total_users = cursor.fetchone()[0]
        
        # Total bookings
        cursor.execute('SELECT COUNT(*) FROM booking')
        total_bookings = cursor.fetchone()[0]
        
        # Available kundas
        cursor.execute('SELECT COUNT(*) FROM homa_kunda WHERE status = "available"')
        available_kundas = cursor.fetchone()[0]
        
        # Approved bookings
        cursor.execute('SELECT COUNT(*) FROM booking WHERE status = "approved"')
        approved_bookings = cursor.fetchone()[0]
        
        # Pending bookings
        cursor.execute('SELECT COUNT(*) FROM booking WHERE status = "pending"')
        pending_bookings = cursor.fetchone()[0]
        
        # Rejected bookings
        cursor.execute('SELECT COUNT(*) FROM booking WHERE status = "rejected"')
        rejected_bookings = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_users': total_users,
                'total_bookings': total_bookings,
                'available_kundas': available_kundas,
                'approved_bookings': approved_bookings,
                'pending_bookings': pending_bookings,
                'rejected_bookings': rejected_bookings,
                'total_kundas': 100
            }
        })
        
    except Exception as e:
        print(f"❌ Admin stats error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to load statistics'
        }), 500

@app.route('/api/admin/bookings', methods=['GET'])
def admin_all_bookings():
    if not is_admin_logged_in():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT b.*, u.name, u.phone, u.email, u.registration_id, u.members_count,
                   k.kunda_number, u.created_at as user_created
            FROM booking b
            JOIN user_registration u ON b.user_id = u.id
            JOIN homa_kunda k ON b.kunda_id = k.id
            ORDER BY b.booked_at DESC
        ''')
        
        bookings = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({
            'success': True,
            'bookings': bookings
        })
        
    except Exception as e:
        print(f"❌ Admin bookings error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to load bookings'
        }), 500

@app.route('/api/admin/users', methods=['GET'])
def admin_all_users():
    if not is_admin_logged_in():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.*, 
                   (SELECT COUNT(*) FROM booking WHERE user_id = u.id) as booking_count,
                   (SELECT status FROM booking WHERE user_id = u.id LIMIT 1) as booking_status,
                   (SELECT kunda_number FROM homa_kunda WHERE id = (SELECT kunda_id FROM booking WHERE user_id = u.id LIMIT 1)) as kunda_number
            FROM user_registration u
            ORDER BY u.created_at DESC
        ''')
        
        users = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({
            'success': True,
            'users': users
        })
        
    except Exception as e:
        print(f"❌ Admin users error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to load users'
        }), 500

@app.route('/api/register', methods=['POST'])
def register_user():
    try:
        data = request.get_json()
        print(f"📝 Registration attempt: {data}")
        
        # Validation
        required_fields = ['name', 'phone', 'email', 'members']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Phone validation
        if not data['phone'].isdigit() or len(data['phone']) != 10:
            return jsonify({
                'success': False,
                'error': 'Phone number must be 10 digits'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if phone already exists
        cursor.execute('SELECT id FROM user_registration WHERE phone = ?', (data['phone'],))
        if cursor.fetchone():
            conn.close()
            return jsonify({
                'success': False,
                'error': 'User with this phone number already registered'
            }), 400
        
        # Generate registration ID
        registration_id = generate_registration_id()
        
        # Create user
        cursor.execute('''
            INSERT INTO user_registration (name, phone, email, members_count, registration_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data['name'].strip(),
            data['phone'].strip(),
            data['email'].strip().lower(),
            int(data['members']),
            registration_id
        ))
        
        user_id = cursor.lastrowid
        
        # Get created user
        cursor.execute('SELECT * FROM user_registration WHERE id = ?', (user_id,))
        user = dict(cursor.fetchone())
        
        conn.commit()
        conn.close()
        
        print(f"✅ User registered: {user['name']} - {registration_id}")
        
        return jsonify({
            'success': True,
            'message': 'Registration successful! You can now book a kunda.',
            'registration_id': registration_id,
            'user': user
        })
        
    except Exception as e:
        print(f"❌ Registration error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Server error. Please try again.'
        }), 500

@app.route('/api/kundas', methods=['GET'])
def get_kundas():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT k.*, u.name as booked_by_name, u.registration_id
            FROM homa_kunda k 
            LEFT JOIN user_registration u ON k.booked_by_id = u.id
            ORDER BY k.kunda_number
        ''')
        
        kundas = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({
            'success': True,
            'kundas': kundas
        })
        
    except Exception as e:
        print(f"❌ Kundas error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to load kundas'
        }), 500

@app.route('/api/bookings', methods=['POST'])
def create_booking():
    try:
        data = request.get_json()
        print(f"📅 Booking attempt: {data}")
        
        if not data.get('user_id') or not data.get('kunda_number'):
            return jsonify({
                'success': False,
                'error': 'Missing user_id or kunda_number'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute('SELECT id FROM user_registration WHERE id = ?', (data['user_id'],))
        user_result = cursor.fetchone()
        if not user_result:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'User not found. Please register first.'
            }), 404
        
        # Check if kunda exists and is available
        cursor.execute('SELECT id, status FROM homa_kunda WHERE kunda_number = ?', (data['kunda_number'],))
        kunda_result = cursor.fetchone()
        if not kunda_result:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Kunda not found'
            }), 404
        
        kunda_id = kunda_result['id']
        kunda_status = kunda_result['status']
        
        if kunda_status != 'available':
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Selected kunda is not available. Please choose another.'
            }), 400
        
        # Check if user already has a booking
        cursor.execute('SELECT id FROM booking WHERE user_id = ?', (data['user_id'],))
        if cursor.fetchone():
            conn.close()
            return jsonify({
                'success': False,
                'error': 'You already have a booking. Only one booking per user is allowed.'
            }), 400
        
        # Create booking
        booking_id = generate_booking_id()
        cursor.execute('''
            INSERT INTO booking (user_id, kunda_id, status, booking_id)
            VALUES (?, ?, ?, ?)
        ''', (data['user_id'], kunda_id, 'pending', booking_id))
        
        # Update kunda status
        cursor.execute('''
            UPDATE homa_kunda SET status = 'booked', booked_by_id = ? 
            WHERE id = ?
        ''', (data['user_id'], kunda_id))
        
        booking_row_id = cursor.lastrowid
        
        # Get created booking with details
        cursor.execute('''
            SELECT b.*, u.name, u.phone, u.email, u.registration_id, u.members_count,
                   k.kunda_number
            FROM booking b
            JOIN user_registration u ON b.user_id = u.id
            JOIN homa_kunda k ON b.kunda_id = k.id
            WHERE b.id = ?
        ''', (booking_row_id,))
        
        booking = dict(cursor.fetchone())
        
        conn.commit()
        conn.close()
        
        print(f"✅ Booking created: Kunda {data['kunda_number']} - {booking_id}")
        
        return jsonify({
            'success': True,
            'message': 'Booking created successfully! Waiting for admin approval.',
            'booking': booking
        })
        
    except Exception as e:
        print(f"❌ Booking error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Booking failed. Please try again.'
        }), 500

@app.route('/api/user/bookings/<phone>', methods=['GET'])
def get_user_bookings(phone):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT b.*, k.kunda_number, u.name, u.email, u.members_count, u.registration_id
            FROM booking b
            JOIN homa_kunda k ON b.kunda_id = k.id
            JOIN user_registration u ON b.user_id = u.id
            WHERE u.phone = ?
            ORDER BY b.booked_at DESC
        ''', (phone,))
        
        bookings = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({
            'success': True,
            'bookings': bookings
        })
        
    except Exception as e:
        print(f"❌ User bookings error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to load bookings'
        }), 500

@app.route('/api/admin/bookings/<action>', methods=['POST'])
def admin_booking_action(action):
    if not is_admin_logged_in():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        booking_id = data.get('booking_id')
        
        if not booking_id:
            return jsonify({
                'success': False,
                'error': 'Missing booking_id'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get booking details
        cursor.execute('''
            SELECT b.*, k.kunda_number, k.id as kunda_id, u.id as user_id, u.name, u.email, u.registration_id, u.members_count
            FROM booking b
            JOIN homa_kunda k ON b.kunda_id = k.id
            JOIN user_registration u ON b.user_id = u.id
            WHERE b.booking_id = ?
        ''', (booking_id,))
        
        booking_result = cursor.fetchone()
        if not booking_result:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Booking not found'
            }), 404
        
        booking_data = dict(booking_result)
        
        if action == 'approve':
            # Approve booking
            cursor.execute('''
                UPDATE booking SET status = 'approved', approved_at = CURRENT_TIMESTAMP
                WHERE booking_id = ?
            ''', (booking_id,))
            
            message = 'Booking approved successfully! User will be notified.'
            
        elif action == 'reject':
            # Reject booking and free up kunda
            cursor.execute('''
                UPDATE booking SET status = 'rejected' WHERE booking_id = ?
            ''', (booking_id,))
            
            cursor.execute('''
                UPDATE homa_kunda SET status = 'available', booked_by_id = NULL
                WHERE id = ?
            ''', (booking_data['kunda_id'],))
            
            message = 'Booking rejected successfully. Kunda is now available.'
        
        else:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Invalid action'
            }), 400
        
        conn.commit()
        conn.close()
        
        print(f"✅ Admin action: {action} on booking {booking_id} by {session.get('admin_username')}")
        
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        print(f"❌ Admin action error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Admin action failed'
        }), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Total registrations
        cursor.execute('SELECT COUNT(*) FROM user_registration')
        total_users = cursor.fetchone()[0]
        
        # Total bookings
        cursor.execute('SELECT COUNT(*) FROM booking')
        total_bookings = cursor.fetchone()[0]
        
        # Available kundas
        cursor.execute('SELECT COUNT(*) FROM homa_kunda WHERE status = "available"')
        available_kundas = cursor.fetchone()[0]
        
        # Approved bookings
        cursor.execute('SELECT COUNT(*) FROM booking WHERE status = "approved"')
        approved_bookings = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_users': total_users,
                'total_bookings': total_bookings,
                'available_kundas': available_kundas,
                'approved_bookings': approved_bookings,
                'total_kundas': 100
            }
        })
        
    except Exception as e:
        print(f"❌ Stats error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to load statistics'
        }), 500

@app.route('/api/check-phone/<phone>', methods=['GET'])
def check_phone(phone):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.*, b.status as booking_status, k.kunda_number 
            FROM user_registration u 
            LEFT JOIN booking b ON u.id = b.user_id 
            LEFT JOIN homa_kunda k ON b.kunda_id = k.id 
            WHERE u.phone = ?
        ''', (phone,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            user_data = dict(result)
            return jsonify({
                'success': True,
                'exists': True,
                'user': user_data
            })
        else:
            return jsonify({
                'success': True,
                'exists': False
            })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Initialize database when app starts
print("🚀 Starting Gayathri Homa Registration System...")
print("📊 Initializing database...")
init_db()
print("✅ Backend server ready!")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 Server running on port {port}")
    print(f"🔑 Admin Password: {ADMIN_PASSWORD}")
    app.run(host='0.0.0.0', port=port, debug=False)