import string
import time
import random
import os
import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from flask import Flask, json, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import logging
import razorpay
import firebase_admin
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials, firestore
from google.api_core import retry, exceptions
from google.cloud.firestore_v1.base_query import FieldFilter

# Suppress unnecessary warnings
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '2'
logging.getLogger('google.auth').setLevel(logging.ERROR)
logging.getLogger('google.cloud').setLevel(logging.ERROR)


# ✅ CRITICAL FIX: Force IPv4 for gRPC/Firestore
os.environ['GRPC_DNS_RESOLVER'] = 'native'

# ✅ Load environment variables
load_dotenv()

# ----------------- CONFIG -----------------
API_PORT = int(os.getenv("PORT", 5000))

# Razorpay keys
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_live_RQXzGyPJabzvVR")
RAZORPAY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "Qz2P5jNuODQKclIQhzyLfqyR")

# Cloudinary keys
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "dz0covpb0")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "283885113357782")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "Y0OZuIHS7MmaV1Ny8mq0FI8gXoY")

# ✅✅✅ ADMIN CONFIG - Direct hardcoded (No .env needed) ✅✅✅
ADMIN_EMAILS = ["admin@vntemplates.com"]  # Comma separated emails allowed
ADMIN_PASSWORD = "admin123"  # Your actual password here
ADMIN_PASSWORD_MD5 = hashlib.md5(ADMIN_PASSWORD.encode()).hexdigest()  # Auto-generate MD5
ADMIN_API_KEY = "My_Boss_123_Anik"
ADMIN_SESSION_TTL_HOURS = 8

print("=" * 60)
print("🔐 ADMIN CREDENTIALS LOADED:")
print(f"   Emails: {ADMIN_EMAILS}")
print(f"   Password: {ADMIN_PASSWORD}")
print(f"   Password MD5: {ADMIN_PASSWORD_MD5}")
print(f"   API Key: {ADMIN_API_KEY}")
print("=" * 60)

def _admin_emails_list():
    return ADMIN_EMAILS

def md5_hex(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()

def now_utc():
    return datetime.now(timezone.utc)

def now_str():
    return now_utc().isoformat()

-Type", "Authorization"],
     max_age=3600)

# ----------------- APP INIT -----------------
app = Flask(__name__)

# ✅ Production-ready CORS configuration
ALLOWED_ORIGINS = [
    "https://vntemplatesdownloader.netlify.app",
    "https://vntemplatesqrdownloader.netlify.app",
    "https://vntemplatesqrdownloader.online",  # ✅ ADDED YOUR DOMAIN
    "https://qrdownloader.online",  # ✅ ADDED (if you have this too)
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]

CORS(app, 
     origins=ALLOWED_ORIGINS,
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization", "x-admin-session", "X-Admin-Session"],
     supports_credentials=True,
     expose_headers=["Content-Type", "Authorization"],
     max_age=3600)

@app.after_request
def after_request(response):
    origin = request.headers.get('Origin')
    if origin in ALLOWED_ORIGINS:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,x-admin-session,X-Admin-Session'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response

# ----------------- Cloudinary -----------------
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)
CLOUDINARY_CONFIGURED = True

def upload_to_cloudinary(fileobj, folder=None, resource_type="image"):
    opts = {}
    if folder: opts["folder"] = folder
    if resource_type == "video": opts["resource_type"] = "video"
    res = cloudinary.uploader.upload(fileobj, **opts)
    return res.get("secure_url")

# ----------------- Razorpay -----------------
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_SECRET))

# ----------------- Firebase -----------------
db = None
try:
    if not firebase_admin._apps:
        # Check if FIREBASE_CREDENTIALS environment variable exists
        firebase_creds = os.getenv("FIREBASE_CREDENTIALS")
        
        if firebase_creds:
            # Use credentials from environment variable (for deployment)
            cred_dict = json.loads(firebase_creds)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase initialized from environment variable")
        elif os.path.exists("serviceAccountKey.json"):
            # Use local file (for local development)
            cred = credentials.Certificate("serviceAccountKey.json")
            firebase_admin.initialize_app(cred)
            print("✅ Firebase initialized from local file")
        else:
            # Fallback to default credentials
            firebase_admin.initialize_app()
            print("✅ Firebase initialized with default credentials")
    
    db = firestore.client()
    print("✅ Firestore client connected")
except Exception as e:
    print(f"❌ Firestore init error: {e}")
    db = None


# ----------------- Health Check & Root Route -----------------
@app.route("/", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "message": "VN Templates Backend is running!",
        "firebase": "connected" if db else "disconnected",
        "cloudinary": "configured" if CLOUDINARY_CONFIGURED else "not configured",
        "razorpay": "configured" if RAZORPAY_KEY_ID else "not configured",
        "timestamp": now_str()
    }), 200

@app.route("/health", methods=["GET"])
def health():
    """Alternative health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "vn-templates-backend",
        "version": "1.0.0"
    }), 200

# ----------------- Helper Functions -----------------
def now_utc():
    return datetime.now(timezone.utc)

def now_str():
    return now_utc().strftime("%Y-%m-%d %H:%M:%S")

def md5_hex(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()

def _admin_emails_list():
    return [e.strip().lower() for e in ADMIN_EMAILS]

def generate_user_id():
    """Generate unique user ID like USER_123456"""
    timestamp = str(int(time.time()))[-6:]
    random_num = str(random.randint(100, 999))
    return f"USER_{timestamp}{random_num}"

def generate_share_code():
    """Generstringique share code like SC8X4M2P (8 # type: ignore characters)"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(8))

def generate_gift_code():
    """Generate unique gift/redeem code like GIFT-ABC123XYZ"""
    chars = string.ascii_uppercase + string.digits
    code = ''.join(random.choice(chars) for _ in range(9))
    return f"GIFT-{code}"

def verify_token_and_check_admin(req):
    """Firebase ID token verify + admin check"""
    auth_header = req.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        return None, None, False
    
    id_token = auth_header.split(" ", 1)[1]
    
    try:
        decoded = firebase_auth.verify_id_token(id_token)
        uid = decoded.get("uid")
        email = decoded.get("email", "").lower()
        is_admin = email in _admin_emails_list() or bool(decoded.get("isAdmin") or decoded.get("admin"))
        
        return uid, decoded, is_admin
    except Exception as e:
        print(f"❌ Token verify failed: {e}")
        return None, None, False

def require_admin(req):
    """3 ways to verify admin"""
    uid, decoded, is_admin = verify_token_and_check_admin(req)
    if is_admin:
        return True, uid, decoded
    
    session_token = req.headers.get("x-admin-session") or req.headers.get("X-Admin-Session")
    if session_token and db:
        try:
            doc = db.collection("admin_sessions").document(session_token).get()
            if doc.exists:
                d = doc.to_dict() or {}
                expires_at = d.get("expiresAt")
                if expires_at:
                    expires_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    if expires_dt > now_utc():
                        return True, d.get("createdBy"), None
        except Exception as e:
            print(f"❌ Session check error: {e}")
    
    header_key = req.headers.get("x-admin-api-key") or req.headers.get("X-ADMIN-API-KEY")
    if header_key and header_key == ADMIN_API_KEY:
        return True, None, None
    
    return False, None, None

    

# ----------------- Admin Login/Logout -----------------
@app.route("/api/admin/login", methods=["POST", "OPTIONS"])
def admin_login():
    if request.method == "OPTIONS":
        return '', 200
    try:
        body = request.json or {}
        email = (body.get("email") or "").strip().lower()
        password = body.get("password") or ""
        
        if not email or not password:
            return jsonify({"error": "email & password required"}), 400
        
        if email not in _admin_emails_list():
            return jsonify({"error": "unauthorized email"}), 403
        
        if md5_hex(password) != ADMIN_PASSWORD_MD5:
            return jsonify({"error": "invalid credentials"}), 403
        
        token = str(uuid.uuid4())
        expires = now_utc() + timedelta(hours=ADMIN_SESSION_TTL_HOURS)
        expires_iso = expires.isoformat()
        
        if db:
            db.collection("admin_sessions").document(token).set({
                "createdAt": now_str(),
                "expiresAt": expires_iso,
                "createdBy": email
            })
        
        return jsonify({
            "token": token,
            "expiresAt": expires_iso,
            "email": email
        }), 200
    except Exception as e:
        print(f"❌ admin_login error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/admin/logout", methods=["POST", "OPTIONS"])
def admin_logout():
    if request.method == "OPTIONS":
        return '', 200
    try:
        token = request.headers.get("x-admin-session") or (request.json or {}).get("token")
        if not token:
            return jsonify({"error": "token required"}), 400
        if db:
            db.collection("admin_sessions").document(token).delete()
        return jsonify({"message": "logged out"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ----------------- Helper Function: Generate Referral Code -----------------
def generate_referral_code(length=8):
    """Generate a unique alphanumeric referral code"""
    characters = string.ascii_uppercase + string.digits
    code = ''.join(random.choices(characters, k=length))
    return code


# ----------------- Register User WITH REFERRAL CODE -----------------
@app.route("/api/register-user", methods=["POST", "OPTIONS"])
def register_user():
    if request.method == "OPTIONS":
        return '', 200

    try:
        body = request.json or {}
        email = (body.get("email") or "").strip().lower()
        display_name = body.get("displayName") or body.get("name") or ""
        provider = body.get("provider") or "email"

        if not email:
            return jsonify({"error": "email required"}), 400
        if not db:
            return jsonify({"error": "Database not available"}), 503

        # Check existing user
        users_query = db.collection("users").where("email", "==", email).limit(1).get(timeout=10)
        if users_query:
            existing_user = users_query[0]
            user_data = existing_user.to_dict()
            print(f"✅ Existing user: {email} | User ID: {user_data.get('userId')}")
            return jsonify({
                "message": "user already exists",
                "uid": existing_user.id,
                "userId": user_data.get("userId"),
                "referralCode": user_data.get("referralCode"),
                "email": email
            }), 200

        # Create new user
        try:
            try:
                existing_firebase = firebase_auth.get_user_by_email(email)
                uid = existing_firebase.uid
            except firebase_auth.UserNotFoundError:
                uid = firebase_auth.create_user(email=email, display_name=display_name).uid

            user_id = generate_user_id()
            referral_code = generate_referral_code()

            db.collection("users").document(uid).set({
                "email": email,
                "displayName": display_name,
                "provider": provider,
                "userId": user_id,
                "referralCode": referral_code,
                "bonusDownloads": 0,
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "isOnline": False,
                "loginCount": 0,
                "likesCount": 0,
                "downloadsCount": 0
            }, merge=True, timeout=10)

            print(f"✅ User registered: {email} | User ID: {user_id} | Referral: {referral_code}")

            return jsonify({
                "message": "user registered",
                "uid": uid,
                "userId": user_id,
                "referralCode": referral_code,
                "email": email
            }), 200

        except Exception as e:
            print(f"❌ Firebase register error: {e}")
            return jsonify({"error": str(e)}), 500

    except Exception as e:
        print(f"❌ register_user error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------- Get User by userId with Retry -----------------
@app.route("/api/users/by-user-id/<user_id>", methods=["GET", "OPTIONS"])
def get_user_by_user_id(user_id):
    if request.method == "OPTIONS":
        return '', 200
    
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            if not db:
                return jsonify({"error": "Database not available"}), 503

            if user_id == "USER_0000":
                return jsonify({"error": "Invalid user ID. Please login again."}), 400

            users_query = db.collection("users").where("userId", "==", user_id).limit(1).get(timeout=10)
            
            for doc in users_query:
                user_data = doc.to_dict()
                return jsonify({
                    "uid": doc.id,
                    "email": user_data.get("email"),
                    "displayName": user_data.get("displayName"),
                    "userId": user_data.get("userId"),
                    "referralCode": user_data.get("referralCode"),
                    "bonusDownloads": user_data.get("bonusDownloads", 0),
                    "isOnline": user_data.get("isOnline", False)
                }), 200
            
            return jsonify({"error": "User not found"}), 404

        except exceptions.DeadlineExceeded:
            if attempt < max_retries - 1:
                print(f"⚠️ Timeout on attempt {attempt + 1}, retrying...")
                time.sleep(retry_delay * (attempt + 1))
                continue
            print(f"❌ Get user by userId timeout after {max_retries} attempts")
            return jsonify({"error": "Service temporarily unavailable", "bonusDownloads": 0}), 503
            
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"⚠️ Error on attempt {attempt + 1}: {e}")
                time.sleep(retry_delay * (attempt + 1))
                continue
            print(f"❌ Get user by userId error: {e}")
            return jsonify({"error": "Service error", "bonusDownloads": 0}), 503

# ----------------- Get User by Firebase UID -----------------
@app.route("/api/users/by-firebase-uid/<firebase_uid>", methods=["GET", "OPTIONS"])
def get_user_by_firebase_uid(firebase_uid):
    if request.method == "OPTIONS":
        return '', 200
    try:
        if not db:
            return jsonify({"error": "Database not available"}), 503

        user_doc = db.collection("users").document(firebase_uid).get(timeout=10)

        if not user_doc.exists:
            return jsonify({"error": "User not found"}), 404

        user_data = user_doc.to_dict()

        return jsonify({
            "uid": firebase_uid,
            "email": user_data.get("email"),
            "displayName": user_data.get("displayName"),
            "userId": user_data.get("userId", "USER_0000"),
            "referralCode": user_data.get("referralCode"),
            "bonusDownloads": user_data.get("bonusDownloads", 0),
            "isOnline": user_data.get("isOnline", False)
        }), 200

    except Exception as e:
        print(f"❌ Get user error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------- Get User by UID -----------------
@app.route("/api/users/<uid>", methods=["GET", "OPTIONS"])
def get_user_by_uid(uid):
    if request.method == "OPTIONS":
        return '', 200
    try:
        if not db:
            return jsonify({"error": "Database not available"}), 503

        user_doc = db.collection("users").document(uid).get(timeout=10)

        if not user_doc.exists:
            return jsonify({"error": "User not found"}), 404

        user_data = user_doc.to_dict()

        return jsonify({
            "uid": uid,
            "email": user_data.get("email"),
            "displayName": user_data.get("displayName"),
            "userId": user_data.get("userId", "USER_0000"),
            "referralCode": user_data.get("referralCode"),
            "bonusDownloads": user_data.get("bonusDownloads", 0),
            "isOnline": user_data.get("isOnline", False),
            "likesCount": user_data.get("likesCount", 0),
            "downloadsCount": user_data.get("downloadsCount", 0)
        }), 200

    except Exception as e:
        print(f"❌ Get user error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------- Use Bonus Download -----------------
@app.route("/api/users/<user_id>/use-bonus-download", methods=["POST", "OPTIONS"])
def use_bonus_download(user_id):
    if request.method == "OPTIONS":
        return '', 200
    
    try:
        if db is None:
            return jsonify({"error": "Database not available"}), 503
        
        users_query = db.collection("users").where("userId", "==", user_id).limit(1).get(timeout=10)
        user_doc_ref = None
        current_bonus = 0
        
        for doc in users_query:
            user_doc_ref = db.collection("users").document(doc.id)
            user_data = doc.to_dict()
            current_bonus = user_data.get("bonusDownloads", 0)
            break
        
        if not user_doc_ref:
            return jsonify({"error": "User not found"}), 404
        
        if current_bonus <= 0:
            return jsonify({"error": "No bonus downloads available"}), 400
        
        new_bonus = max(0, current_bonus - 1)
        user_doc_ref.update({
            "bonusDownloads": new_bonus,
            "lastBonusUsed": now_str()
        }, timeout=10)
        
        print(f"✅ Bonus download used: {user_id} | Remaining: {new_bonus}")
        
        return jsonify({
            "message": "Bonus download used successfully",
            "bonusDownloads": new_bonus
        }), 200
        
    except Exception as e:
        print(f"❌ Use bonus download error: {e}")
        return jsonify({"error": str(e)}), 500

# ==================== PROMO CODE (Referral) SYSTEM ====================
@app.route("/api/promo/apply", methods=["POST", "OPTIONS"])
def apply_promo_code():
    if request.method == "OPTIONS":
        return '', 200
    
    try:
        body = request.json or {}
        user_id = body.get("userId")
        promo_code = body.get("promoCode", "").strip().upper()
        
        if not user_id or not promo_code:
            return jsonify({"error": "userId and promoCode required"}), 400
        
        if db is None:
            return jsonify({"error": "Database not available"}), 503
        
        owner_query = db.collection("users").where("referralCode", "==", promo_code).limit(1).get(timeout=10)
        
        if len(owner_query) == 0:
            return jsonify({"error": "Invalid promo code"}), 404
        
        owner_doc = owner_query[0]
        owner_data = owner_doc.to_dict()
        owner_user_id = owner_data.get("userId")
        
        if owner_user_id == user_id:
            return jsonify({"error": "Cannot use your own referral code"}), 400
        
        user_query = db.collection("users").where("userId", "==", user_id).limit(1).get(timeout=10)
        
        if len(user_query) == 0:
            return jsonify({"error": "User not found"}), 404
        
        user_doc = user_query[0]
        user_doc_ref = db.collection("users").document(user_doc.id)
        current_user_data = user_doc.to_dict()
        
        used_codes = current_user_data.get("usedPromoCodes", [])
        if promo_code in used_codes:
            return jsonify({"error": "Promo code already used"}), 400
        
        BONUS_DOWNLOADS = 10
        current_bonus = current_user_data.get("bonusDownloads", 0)
        
        user_doc_ref.update({
            "bonusDownloads": current_bonus + BONUS_DOWNLOADS,
            "usedPromoCodes": firestore.ArrayUnion([promo_code]),
            "lastPromoApplied": now_str()
        }, timeout=10)
        
        owner_ref = db.collection("users").document(owner_doc.id)
        owner_current_bonus = owner_data.get("bonusDownloads", 0)
        
        owner_ref.update({
            "bonusDownloads": owner_current_bonus + BONUS_DOWNLOADS,
            "referralCount": owner_data.get("referralCount", 0) + 1
        }, timeout=10)
        
        print(f"✅ Promo applied: {promo_code} | User: {user_id} | Bonus: {BONUS_DOWNLOADS}")
        
        return jsonify({
            "message": f"Promo code applied! You received {BONUS_DOWNLOADS} bonus downloads",
            "bonusDownloads": current_bonus + BONUS_DOWNLOADS
        }), 200
        
    except Exception as e:
        print(f"❌ Apply promo error: {e}")
        return jsonify({"error": str(e)}), 500

# ==================== GIFT CODE SYSTEM ====================
@app.route("/api/admin/gift-codes", methods=["GET", "POST", "OPTIONS"])
def gift_codes():
    if request.method == "OPTIONS":
        return '', 200
    
    if request.method == "GET":
        ok, admin_uid, decoded = require_admin(request)
        if not ok:
            return jsonify({"error": "Unauthorized"}), 403
        
        try:
            if db is None:
                return jsonify([]), 200
            
            search_query = request.args.get("search", "").strip().lower()
            
            gift_codes_ref = db.collection("gift_codes").get(timeout=10)
            codes_list = []
            
            for doc in gift_codes_ref:
                gift_data = doc.to_dict() or {}
                
                code_info = {
                    "id": doc.id,
                    "code": gift_data.get("code"),
                    "plan": gift_data.get("plan"),
                    "maxUses": gift_data.get("maxUses", 1),
                    "usedCount": gift_data.get("usedCount", 0),
                    "validUntil": gift_data.get("validUntil"),
                    "description": gift_data.get("description", ""),
                    "createdAt": gift_data.get("createdAt"),
                    "createdBy": gift_data.get("createdBy"),
                    "status": gift_data.get("status", "active"),
                    "usedBy": gift_data.get("usedBy", []),
                    "redemptions": gift_data.get("redemptions", {})
                }
                
                if search_query:
                    if search_query in gift_data.get("code", "").lower() or \
                       search_query in gift_data.get("plan", "").lower():
                        codes_list.append(code_info)
                else:
                    codes_list.append(code_info)
            
            codes_list.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
            
            return jsonify(codes_list), 200
            
        except Exception as e:
            print(f"❌ Get gift codes error: {e}")
            return jsonify({"error": str(e)}), 500
    
    elif request.method == "POST":
        ok, admin_uid, decoded = require_admin(request)
        if not ok:
            return jsonify({"error": "Unauthorized"}), 403
        
        try:
            if db is None:
                return jsonify({"error": "Database not available"}), 503
            
            body = request.json or {}
            plan = body.get("plan", "Plus")
            max_uses = body.get("maxUses", 1)
            valid_until = body.get("validUntil")
            description = body.get("description", "")
            
            if plan not in ["Go", "Plus", "Pro", "Unlimited"]:
                return jsonify({"error": "Invalid plan"}), 400
            
            expires_at = None
            if valid_until:
                try:
                    expires_at = datetime.fromisoformat(valid_until.replace('Z', '+00:00'))
                except:
                    return jsonify({"error": "Invalid date format"}), 400
            else:
                expires_at = now_utc() + timedelta(days=30)
            
            code = generate_gift_code()
            
            gift_data = {
                "code": code,
                "plan": plan,
                "maxUses": max_uses,
                "usedCount": 0,
                "validUntil": expires_at.isoformat(),
                "description": description,
                "createdAt": now_str(),
                "createdBy": admin_uid or "admin",
                "status": "active",
                "usedBy": []
            }
            
            db.collection("gift_codes").document(code).set(gift_data, timeout=10)
            
            print(f"✅ Gift code created: {code} | Plan: {plan} | Max Uses: {max_uses}")
            
            return jsonify({
                "message": "Gift code created successfully",
                "code": code,
                "plan": plan,
                "validUntil": expires_at.isoformat()
            }), 200
            
        except Exception as e:
            print(f"❌ Create gift code error: {e}")
            return jsonify({"error": str(e)}), 500

@app.route("/api/gift-codes/redeem", methods=["POST", "OPTIONS"])
def redeem_gift_code():
    if request.method == "OPTIONS":
        return '', 200
    
    try:
        body = request.json or {}
        user_id = body.get("userId")
        code = body.get("code", "").strip().upper()
        
        if not user_id or not code:
            return jsonify({"error": "userId and code required"}), 400
        
        if db is None:
            return jsonify({"error": "Database not available"}), 503
        
        gift_doc = db.collection("gift_codes").document(code).get(timeout=10)
        
        if not gift_doc.exists:
            return jsonify({"error": "Invalid gift code"}), 404
        
        gift_data = gift_doc.to_dict()
        
        valid_until = gift_data.get("validUntil")
        if valid_until:
            expiry_date = datetime.fromisoformat(valid_until.replace('Z', '+00:00'))
            if expiry_date < now_utc():
                return jsonify({"error": "Gift code has expired"}), 400
        
        used_count = gift_data.get("usedCount", 0)
        max_uses = gift_data.get("maxUses", 1)
        
        if used_count >= max_uses:
            return jsonify({"error": "Gift code has reached maximum uses"}), 400
        
        used_by = gift_data.get("usedBy", [])
        if user_id in used_by:
            return jsonify({"error": "You have already used this gift code"}), 400
        
        user_query = db.collection("users").where("userId", "==", user_id).limit(1).stream()
        user_firebase_uid = None
        user_email = None
        
        for doc in user_query:
            user_firebase_uid = doc.id
            user_email = doc.to_dict().get("email")
            break
        
        if not user_firebase_uid:
            return jsonify({"error": "User not found"}), 404
        
        plan = gift_data.get("plan", "Plus")
        plan_duration = {
            "Go": 30,
            "Plus": 60,
            "Pro": 90,
            "Unlimited": 365
        }
        
        days = plan_duration.get(plan, 30)
        expires_at = now_utc() + timedelta(days=days)
        
        subscription_data = {
            "userId": user_id,
            "plan": plan,
            "status": "active",
            "paymentId": f"GIFT-{code}",
            "orderId": f"GIFT-{code}",
            "signature": "gift_code",
            "createdAt": now_str(),
            "expiresAt": expires_at.isoformat(),
            "source": "gift_code",
            "giftCode": code
        }
        
        db.collection("subscriptions").add(subscription_data)
        
        db.collection("gift_codes").document(code).update({
            "usedCount": used_count + 1,
            "usedBy": firestore.ArrayUnion([user_id]),
            f"redemptions.{user_id}": {
                "email": user_email,
                "redeemedAt": now_str()
            }
        })
        
        print(f"✅ Gift code redeemed: {code} | User: {user_id} | Plan: {plan}")
        
        return jsonify({
            "message": f"Gift code redeemed! You received {plan} plan for {days} days",
            "plan": plan,
            "expiresAt": expires_at.isoformat()
        }), 200
        
    except Exception as e:
        print(f"❌ Redeem gift code error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/admin/gift-codes/<code>", methods=["DELETE", "OPTIONS"])
def delete_gift_code(code):
    if request.method == "OPTIONS":
        return '', 200
    
    ok, admin_uid, decoded = require_admin(request)
    if not ok:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        if db is None:
            return jsonify({"error": "Database not available"}), 500
        
        db.collection("gift_codes").document(code).delete()
        
        print(f"✅ Gift code deleted: {code}")
        
        return jsonify({"message": "Gift code deleted successfully"}), 200
        
    except Exception as e:
        print(f"❌ Delete gift code error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/admin/gift-codes/<code>/toggle", methods=["POST", "OPTIONS"])
def toggle_gift_code(code):
    if request.method == "OPTIONS":
        return '', 200
    
    ok, admin_uid, decoded = require_admin(request)
    if not ok:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        if db is None:
            return jsonify({"error": "Database not available"}), 500
        
        gift_doc = db.collection("gift_codes").document(code).get()
        
        if not gift_doc.exists:
            return jsonify({"error": "Gift code not found"}), 404
        
        current_status = gift_doc.to_dict().get("status", "active")
        new_status = "inactive" if current_status == "active" else "active"
        
        db.collection("gift_codes").document(code).update({"status": new_status})
        
        print(f"✅ Gift code toggled: {code} | New status: {new_status}")
        
        return jsonify({"message": "Status updated", "status": new_status}), 200
        
    except Exception as e:
        print(f"❌ Toggle gift code error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------- User Ping -----------------
@app.route("/api/users/<user_id>/ping", methods=["POST", "OPTIONS"])
def ping_user(user_id):
    if request.method == "OPTIONS":
        return '', 200
    return jsonify({"message": f"Ping received for user {user_id}"}), 200

# ----------------- Online/Offline Status -----------------
@app.route("/api/users/<uid>/set-online", methods=["POST", "OPTIONS"])
def set_user_online(uid):
    if request.method == "OPTIONS":
        return '', 200
    
    try:
        body = request.get_json(silent=True) or {}
        is_online = bool(body.get("isOnline", False))
        current_time = now_utc()
        
        if db is None:
            return jsonify({"error": "Firestore not configured"}), 500

        user_ref = db.collection("users").document(uid)
        updates = {
            "isOnline": is_online,
            "lastActiveAt": current_time.isoformat()
        }

        if is_online:
            user_doc = user_ref.get()
            if user_doc.exists:
                data = user_doc.to_dict()
                current_count = data.get("loginCount", 0)
                updates["loginCount"] = current_count + 1
                updates["lastLogin"] = now_str()
            else:
                updates["loginCount"] = 1
                updates["lastLogin"] = now_str()

        user_ref.set(updates, merge=True)
        print(f"✅ User {uid} status: {'ONLINE' if is_online else 'OFFLINE'}")
        return jsonify({"message": "User status updated", "isOnline": is_online}), 200
        
    except Exception as e:
        print(f"❌ Set Online/Offline Error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------- Auto Offline Check -----------------
@app.route("/api/admin/auto-offline", methods=["POST", "OPTIONS"])
def auto_offline_check():
    if request.method == "OPTIONS":
        return '', 200
    
    try:
        if db is None:
            return jsonify({"error": "Firestore not configured"}), 500

        users_ref = db.collection("users").stream()
        now_time = now_utc()
        inactive_threshold = timedelta(minutes=10)
        offline_count = 0

        for doc in users_ref:
            user = doc.to_dict() or {}
            last_active = user.get("lastActiveAt")
            if last_active:
                try:
                    last_active_dt = datetime.fromisoformat(last_active)
                    if (now_time - last_active_dt) > inactive_threshold:
                        db.collection("users").document(doc.id).update({"isOnline": False})
                        offline_count += 1
                except ValueError:
                    continue

        return jsonify({"message": f"{offline_count} users set offline"}), 200
        
    except Exception as e:
        print(f"❌ Auto Offline Error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------- Razorpay Create Order -----------------
@app.route("/api/create-order", methods=["POST", "OPTIONS"])
def create_order():
    if request.method == "OPTIONS":
        return '', 200
    try:
        data = request.json or {}
        plan = data.get("plan", "one-time")
        user_id = data.get("userId")

        price_map = {
            "Go": 49,
            "Plus": 99,
            "Pro": 149,
            "Unlimited": 199
        }

        amount = price_map.get(plan, 49)

        order_data = {
            "amount": amount * 100,
            "currency": "INR",
            "payment_capture": 1
        }
        order = razorpay_client.order.create(order_data)

        if not order or "id" not in order:
            return jsonify({"error": "Failed to create Razorpay order"}), 500

        return jsonify({
            "orderId": order.get("id"),
            "amount": amount,
            "currency": "INR",
            "key": RAZORPAY_KEY_ID,
            "userId": user_id,
            "plan": plan
        }), 200

    except Exception as e:
        print(f"❌ Order Error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------- Save Subscription -----------------
@app.route("/api/save-subscription", methods=["POST", "OPTIONS"])
def save_subscription():
    if request.method == "OPTIONS":
        return '', 200
    
    try:
        data = request.json or {}
        user_id = data.get("userId")
        plan = data.get("plan")
        payment_id = data.get("paymentId")
        order_id = data.get("orderId")
        signature = data.get("signature")
        
        if not all([user_id, plan, payment_id, order_id]):
            return jsonify({"error": "Missing required fields"}), 400
        
        if db is None:
            return jsonify({"error": "Database not available"}), 500
        
        plan_duration = {
            "Go": 30,
            "Plus": 60,
            "Pro": 90,
            "Unlimited": 365
        }
        
        days = plan_duration.get(plan, 30)
        expires_at = now_utc() + timedelta(days=days)
        
        subscription_data = {
            "userId": user_id,
            "plan": plan,
            "status": "active",
            "paymentId": payment_id,
            "orderId": order_id,
            "signature": signature,
            "createdAt": now_str(),
            "expiresAt": expires_at.isoformat(),
            "source": "razorpay"
        }
        
        db.collection("subscriptions").add(subscription_data)
        
        print(f"✅ Subscription saved: {user_id} | Plan: {plan}")
        
        return jsonify({
            "message": "Subscription saved successfully",
            "expiresAt": expires_at.isoformat()
        }), 200
        
    except Exception as e:
        print(f"❌ Save subscription error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------- Get User Subscriptions -----------------
@app.route("/api/users/<user_id>/subscriptions", methods=["GET", "OPTIONS"])
def get_user_subscriptions(user_id):
    if request.method == "OPTIONS":
        return '', 200
    try:
        if db is None:
            return jsonify({"error": "Database not available"}), 500
        
        subs_ref = db.collection("subscriptions").where("userId", "==", user_id).stream()
        subscriptions = []
        
        for doc in subs_ref:
            sub_data = doc.to_dict()
            sub_data["id"] = doc.id
            subscriptions.append(sub_data)
        
        subscriptions.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
        
        return jsonify(subscriptions), 200
        
    except Exception as e:
        print(f"❌ Get subscriptions error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------- Templates Redirect (Compatibility) -----------------
@app.route("/templates", methods=["GET", "OPTIONS"])
def templates_redirect():
    """Redirect /templates to /api/templates for compatibility"""
    if request.method == "OPTIONS":
        return '', 200
    
    try:
        if db is None:
            return jsonify([]), 200
        
        templates_ref = db.collection("templates").stream()
        templates = []
        
        for doc in templates_ref:
            t = doc.to_dict() or {}
            t["id"] = doc.id
            t["likesCount"] = len(t.get("likes", []))
            t["videoUrl"] = t.get("videoUrl") or t.get("video")
            t["thumbnailUrl"] = t.get("thumbnailUrl") or t.get("thumbnail")
            t["qrImageUrl"] = t.get("qrImageUrl") or t.get("qr") or None
            t["qrUrl"] = t.get("qrUrl") or None
            t["musicUrl"] = t.get("musicUrl") or t.get("music")
            t["premium"] = t.get("premium", False)
            templates.append(t)
        
        return jsonify(templates), 200
        
    except Exception as e:
        print(f"❌ Get Templates Error: {e}")
        return jsonify({"error": str(e)}), 500
    
# ----------------- Check Subscription Status -----------------
@app.route('/api/subscriptions/check/<user_id>', methods=['GET', 'OPTIONS'])
def check_subscription(user_id):
    if request.method == "OPTIONS":
        return '', 200

    try:
        if db is None:
            return jsonify({"isPremium": False}), 200

        # 🔹 Fetch only active subscriptions for this user
        subs_snapshot = db.collection('subscriptions') \
            .where('userId', '==', user_id) \
            .where('status', '==', 'active') \
            .stream()

        is_premium = False

        # 🔹 Current UTC time
        now_utc = datetime.now(timezone.utc)

        # 🔹 Loop through subscriptions
        for doc in subs_snapshot:
            data = doc.to_dict()
            expires_at = data.get('expiresAt')

            if expires_at:
                try:
                    # Convert string to datetime safely
                    expiry_date = datetime.fromisoformat(
                        expires_at.replace('Z', '+00:00')
                    )
                    if expiry_date > now_utc:
                        is_premium = True
                        break
                except Exception as e:
                    print(f"⚠️ Expiry parse error: {e}")
                    continue

        return jsonify({'isPremium': is_premium}), 200

    except Exception as e:
        print(f"❌ Check subscription error: {e}")
        return jsonify({'error': 'Failed to check premium status'}), 500

# ----------------- Admin: Get All Subscriptions -----------------
@app.route("/api/admin/subscriptions", methods=["GET", "OPTIONS"])
def admin_subscriptions():
    if request.method == "OPTIONS":
        return '', 200
    
    ok, admin_uid, decoded = require_admin(request)
    if not ok:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        if db is None:
            return jsonify({"error": "Firestore not configured"}), 500
        
        search_query = request.args.get("search", "").strip().lower()
        
        subscriptions_ref = db.collection("subscriptions").stream()
        subscriptions_list = []
        
        for doc in subscriptions_ref:
            sub_data = doc.to_dict() or {}
            user_id = sub_data.get("userId")
            
            user_email = None
            display_name = None
            if user_id:
                try:
                    users_query = db.collection("users").where("userId", "==", user_id).limit(1).stream()
                    
                    for user_doc in users_query:
                        user_data = user_doc.to_dict() or {}
                        user_email = user_data.get("email")
                        display_name = user_data.get("displayName")
                        break
                except Exception as e:
                    print(f"⚠️ Error fetching user {user_id}: {e}")
            
            subscription = {
                "id": doc.id,
                "userId": user_id,
                "userEmail": user_email,
                "displayName": display_name,
                "plan": sub_data.get("plan"),
                "status": sub_data.get("status"),
                "paymentId": sub_data.get("paymentId"),
                "orderId": sub_data.get("orderId"),
                "signature": sub_data.get("signature"),
                "createdAt": sub_data.get("createdAt"),
                "expiresAt": sub_data.get("expiresAt"),
                "source": sub_data.get("source", "razorpay"),
                "giftCode": sub_data.get("giftCode")
            }
            
            if search_query:
                if (user_email and search_query in user_email.lower()) or \
                   (user_id and search_query in user_id.lower()) or \
                   (display_name and search_query in display_name.lower()):
                    subscriptions_list.append(subscription)
            else:
                subscriptions_list.append(subscription)
        
        subscriptions_list.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
        
        return jsonify(subscriptions_list), 200
        
    except Exception as e:
        print(f"❌ Admin subscriptions error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------- Admin: Get Subscription Stats -----------------
@app.route("/api/admin/subscription-stats", methods=["GET", "OPTIONS"])
def admin_subscription_stats():
    if request.method == "OPTIONS":
        return '', 200
    
    ok, admin_uid, decoded = require_admin(request)
    if not ok:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        if db is None:
            return jsonify({"error": "Firestore not configured"}), 500
        
        subscriptions_ref = db.collection("subscriptions").stream()
        
        total = 0
        active = 0
        expired = 0
        revenue = 0
        gift_count = 0
        plan_breakdown = {"Go": 0, "Plus": 0, "Pro": 0, "Unlimited": 0}
        
        price_map = {"Go": 49, "Plus": 99, "Pro": 149, "Unlimited": 199}
        
        for doc in subscriptions_ref:
            sub_data = doc.to_dict() or {}
            total += 1
            
            source = sub_data.get("source", "razorpay")
            if source == "gift_code":
                gift_count += 1
            
            expires_at = sub_data.get("expiresAt")
            if expires_at:
                try:
                    expiry_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    if expiry_date > now_utc():
                        active += 1
                    else:
                        expired += 1
                except:
                    expired += 1
            
            plan = sub_data.get("plan", "")
            if plan in price_map:
                if source != "gift_code":
                    revenue += price_map[plan]
                plan_breakdown[plan] += 1
        
        return jsonify({
            "total": total,
            "active": active,
            "expired": expired,
            "revenue": revenue,
            "giftCodeRedemptions": gift_count,
            "planBreakdown": [
                {"name": k, "value": v} for k, v in plan_breakdown.items() if v > 0
            ]
        }), 200
        
    except Exception as e:
        print(f"❌ Subscription stats error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------- Admin: Delete Subscription -----------------
@app.route("/api/admin/subscriptions/<subscription_id>", methods=["DELETE", "OPTIONS"])
def admin_delete_subscription(subscription_id):
    if request.method == "OPTIONS":
        return '', 200
    
    ok, admin_uid, decoded = require_admin(request)
    if not ok:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        if db is None:
            return jsonify({"error": "Firestore not configured"}), 500
        
        doc_ref = db.collection("subscriptions").document(subscription_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return jsonify({"error": "Subscription not found"}), 404
        
        doc_ref.delete()
        print(f"✅ Subscription deleted: {subscription_id}")
        
        return jsonify({"message": "Subscription deleted successfully"}), 200
        
    except Exception as e:
        print(f"❌ Delete subscription error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------- Admin: Extend Subscription -----------------
@app.route("/api/admin/subscriptions/<subscription_id>/extend", methods=["POST", "OPTIONS"])
def admin_extend_subscription(subscription_id):
    if request.method == "OPTIONS":
        return '', 200
    
    ok, admin_uid, decoded = require_admin(request)
    if not ok:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        if db is None:
            return jsonify({"error": "Firestore not configured"}), 500
        
        body = request.json or {}
        extra_days = body.get("days", 30)
        
        doc_ref = db.collection("subscriptions").document(subscription_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return jsonify({"error": "Subscription not found"}), 404
        
        sub_data = doc.to_dict() or {}
        current_expiry = sub_data.get("expiresAt")
        
        if current_expiry:
            expiry_date = datetime.fromisoformat(current_expiry.replace('Z', '+00:00'))
            
            if expiry_date < now_utc():
                new_expiry = now_utc() + timedelta(days=extra_days)
            else:
                new_expiry = expiry_date + timedelta(days=extra_days)
            
            doc_ref.update({
                "expiresAt": new_expiry.isoformat(),
                "extendedAt": now_str(),
                "extendedBy": admin_uid or "admin"
            })
            
            return jsonify({
                "message": "Subscription extended successfully",
                "newExpiryDate": new_expiry.isoformat()
            }), 200
        
        return jsonify({"error": "Invalid expiry date"}), 400
        
    except Exception as e:
        print(f"❌ Extend subscription error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------- Templates CRUD -----------------
@app.route("/api/templates", methods=["GET", "POST", "OPTIONS"])
def templates():
    if request.method == "OPTIONS":
        return '', 200
    
    if request.method == "GET":
        try:
            if db is None:
                return jsonify([]), 200
            templates_ref = db.collection("templates").stream()
            templates = []
            for doc in templates_ref:
                t = doc.to_dict() or {}
                t["id"] = doc.id
                t["likesCount"] = len(t.get("likes", []))
                t["videoUrl"] = t.get("videoUrl") or t.get("video")
                t["thumbnailUrl"] = t.get("thumbnailUrl") or t.get("thumbnail")
                t["qrImageUrl"] = t.get("qrImageUrl") or t.get("qr") or None
                t["qrUrl"] = t.get("qrUrl") or None
                t["musicUrl"] = t.get("musicUrl") or t.get("music")
                t["premium"] = t.get("premium", False)
                templates.append(t)
            return jsonify(templates), 200
        except Exception as e:
            print(f"❌ Get Templates Error: {e}")
            return jsonify({"error": str(e)}), 500

    elif request.method == "POST":
        ok, admin_uid, decoded = require_admin(request)
        if not ok:
            return jsonify({"error": "Unauthorized"}), 403

        try:
            form = request.form
            files = request.files

            template_id = form.get("id") or str(uuid.uuid4())
            title = form.get("title")
            category = form.get("category")
            tags = [t.strip() for t in form.get("tags", "").split(",") if t.strip()]
            premium = form.get("premium", "false").lower() == "true"

            video_url = thumbnail_url = qr_image_url = music_url = None
            qr_url_hidden = form.get("qrUrl", "")

            if "video" in files and CLOUDINARY_CONFIGURED:
                video_url = upload_to_cloudinary(files["video"], folder="templates/videos", resource_type="video")

            if "thumbnail" in files and CLOUDINARY_CONFIGURED:
                thumbnail_url = upload_to_cloudinary(files["thumbnail"], folder="templates/thumbnails", resource_type="image")

            if "qr" in files and CLOUDINARY_CONFIGURED:
                qr_image_url = upload_to_cloudinary(files["qr"], folder="templates/qr", resource_type="image")

            if "music" in files and CLOUDINARY_CONFIGURED:
                music_url = upload_to_cloudinary(files["music"], folder="templates/music", resource_type="video")

            doc = {
                "title": title,
                "category": category,
                "tags": tags,
                "video": video_url,
                "thumbnail": thumbnail_url,
                "qrImageUrl": qr_image_url,
                "music": music_url,
                "qrUrl": qr_url_hidden if qr_url_hidden else None,
                "videoUrl": video_url,
                "thumbnailUrl": thumbnail_url,
                "musicUrl": music_url,
                "premium": premium,
                "likes": [],
                "downloads": 0,
                "createdAt": now_str()
            }

            if db:
                db.collection("templates").document(template_id).set(doc)
            return jsonify({"message": "Template uploaded", "id": template_id}), 200
        except Exception as e:
            print(f"❌ Upload Template Error: {e}")
            return jsonify({"error": str(e)}), 500

# ----------------- Toggle Premium Status -----------------
@app.route('/api/admin/templates/<template_id>/toggle-premium', methods=['POST', 'OPTIONS'])
def toggle_premium_status(template_id):
    if request.method == "OPTIONS":
        return '', 200
    
    ok, admin_uid, decoded = require_admin(request)
    if not ok:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        if db is None:
            return jsonify({"error": "Firestore not configured"}), 500
        
        data = request.json or {}
        is_premium = data.get('premium', False)
        
        template_ref = db.collection('templates').document(template_id)
        template_doc = template_ref.get()
        
        if not template_doc.exists:
            return jsonify({'error': 'Template not found'}), 404
        
        template_ref.update({'premium': bool(is_premium)})
        
        print(f"✅ Template {template_id} premium status: {is_premium}")
        return jsonify({'success': True, 'premium': is_premium}), 200
    
    except Exception as e:
        print(f"❌ Toggle premium error: {e}")
        return jsonify({'error': str(e)}), 500

# ----------------- Get/Update/Delete Single Template -----------------
@app.route("/api/templates/<template_id>", methods=["GET", "PUT", "DELETE", "OPTIONS"])
def template_operations(template_id):
    if request.method == "OPTIONS":
        return '', 200
    
    if request.method == "GET":
        try:
            if db is None:
                return jsonify({"error": "Firestore not configured"}), 500
            doc_ref = db.collection("templates").document(template_id)
            doc = doc_ref.get()
            if not doc.exists:
                return jsonify({"error": "Template not found"}), 404
            t = doc.to_dict() or {}
            t["id"] = doc.id
            t["likesCount"] = len(t.get("likes", []))
            t["videoUrl"] = t.get("videoUrl") or t.get("video")
            t["thumbnailUrl"] = t.get("thumbnailUrl") or t.get("thumbnail")
            t["qrImageUrl"] = t.get("qrImageUrl") or t.get("qr") or None
            t["qrUrl"] = t.get("qrUrl") or None
            t["musicUrl"] = t.get("musicUrl") or t.get("music")
            t["premium"] = t.get("premium", False)
            return jsonify(t), 200
        except Exception as e:
            print(f"❌ Get Template Error: {e}")
            return jsonify({"error": str(e)}), 500

    elif request.method == "PUT":
        ok, admin_uid, decoded = require_admin(request)
        if not ok:
            return jsonify({"error": "Unauthorized"}), 403
        try:
            if db is None:
                return jsonify({"error": "Firestore not configured"}), 500
            doc_ref = db.collection("templates").document(template_id)
            if not doc_ref.get().exists:
                return jsonify({"error": "Template not found"}), 404

            form = request.form
            files = request.files
            update_data = {}

            if "title" in form: update_data["title"] = form.get("title")
            if "category" in form: update_data["category"] = form.get("category")
            if "tags" in form: update_data["tags"] = [t.strip() for t in form.get("tags", "").split(",") if t.strip()]
            if "premium" in form: update_data["premium"] = form.get("premium", "false").lower() == "true"

            if "qrUrl" in form:
                update_data["qrUrl"] = form.get("qrUrl") or None

            if "video" in files:
                if not CLOUDINARY_CONFIGURED:
                    return jsonify({"error": "Cloudinary not configured"}), 500
                url = upload_to_cloudinary(files["video"], folder="templates/videos", resource_type="video")
                update_data["video"] = url
                update_data["videoUrl"] = url
            if "thumbnail" in files:
                if not CLOUDINARY_CONFIGURED:
                    return jsonify({"error": "Cloudinary not configured"}), 500
                url = upload_to_cloudinary(files["thumbnail"], folder="templates/thumbnails", resource_type="image")
                update_data["thumbnail"] = url
                update_data["thumbnailUrl"] = url
            if "qr" in files:
                if not CLOUDINARY_CONFIGURED:
                    return jsonify({"error": "Cloudinary not configured"}), 500
                url = upload_to_cloudinary(files["qr"], folder="templates/qr", resource_type="image")
                update_data["qrImageUrl"] = url
            if "music" in files:
                if not CLOUDINARY_CONFIGURED:
                    return jsonify({"error": "Cloudinary not configured"}), 500
                url = upload_to_cloudinary(files["music"], folder="templates/music", resource_type="video")
                update_data["music"] = url
                update_data["musicUrl"] = url

            update_data["updatedAt"] = now_str()
            doc_ref.update(update_data)
            return jsonify({"message": "Template updated", "id": template_id}), 200
        except Exception as e:
            print(f"❌ Update Template Error: {e}")
            return jsonify({"error": str(e)}), 500

    elif request.method == "DELETE":
        ok, admin_uid, decoded = require_admin(request)
        if not ok:
            return jsonify({"error": "Unauthorized"}), 403
        try:
            if db is None:
                return jsonify({"error": "Firestore not configured"}), 500
            doc_ref = db.collection("templates").document(template_id)
            if not doc_ref.get().exists:
                return jsonify({"error": "Template not found"}), 404
            doc_ref.delete()
            return jsonify({"message": "Template deleted"}), 200
        except Exception as e:
            print(f"❌ Delete Template Error: {e}")
            return jsonify({"error": str(e)}), 500

# ----------------- Remove Media from Template -----------------
@app.route("/api/templates/<template_id>/remove-media", methods=["POST", "OPTIONS"])
def remove_media(template_id):
    if request.method == "OPTIONS":
        return '', 200
    ok, admin_uid, decoded = require_admin(request)
    if not ok:
        return jsonify({"error": "Unauthorized"}), 403
    try:
        if db is None:
            return jsonify({"error": "Firestore not configured"}), 500
        body = request.json or {}
        media_type = body.get("mediaType")
        if media_type not in ("thumbnail", "qr", "video", "music"):
            return jsonify({"error": "Invalid mediaType"}), 400
        field_map = {
            "thumbnail": ["thumbnail", "thumbnailUrl"],
            "qr": ["qrImageUrl", "qrUrl"],
            "video": ["video", "videoUrl"],
            "music": ["music", "musicUrl"],
        }
        fields = field_map[media_type]
        updates = {f: None for f in fields}
        db.collection("templates").document(template_id).update(updates)
        return jsonify({"message": f"{media_type} removed"}), 200
    except Exception as e:
        print(f"❌ Remove media error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------- Get All Users -----------------
@app.route("/api/users", methods=["GET", "OPTIONS"])
def get_users():
    if request.method == "OPTIONS":
        return '', 200
    try:
        if db is None:
            return jsonify([]), 200
        
        search_query = request.args.get("search", "").strip().lower()
        
        users_ref = db.collection("users").stream()
        users = []
        seen_emails = set()
        
        for doc in users_ref:
            u = doc.to_dict() or {}
            email = u.get("email")
            
            if not email or email in seen_emails:
                continue
            
            seen_emails.add(email)
            
            user_data = {
                "id": doc.id,
                "email": email,
                "displayName": u.get("displayName") or u.get("name") or "Unknown",
                "userId": u.get("userId", "N/A"),
                "referralCode": u.get("referralCode", ""),
                "bonusDownloads": u.get("bonusDownloads", 0),
                "referralCount": u.get("referralCount", 0),
                "likesCount": u.get("likesCount", 0),
                "downloadsCount": u.get("downloadsCount", 0),
                "loginCount": u.get("loginCount", 0),
                "lastLogin": u.get("lastLogin"),
                "isOnline": u.get("isOnline", False),
                "lastActiveAt": u.get("lastActiveAt")
            }
            
            if search_query:
                if search_query in email.lower() or \
                   search_query in user_data["userId"].lower() or \
                   search_query in user_data["displayName"].lower():
                    users.append(user_data)
            else:
                users.append(user_data)
        
        users.sort(key=lambda x: (not x.get("isOnline", False), x.get("lastActiveAt", "")), reverse=True)
        
        return jsonify(users), 200
    except Exception as e:
        print(f"❌ Get Users Error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------- Track Template Download -----------------
@app.route("/api/templates/<template_id>/download", methods=["POST", "OPTIONS"])
def track_download(template_id):
    if request.method == "OPTIONS":
        return '', 200
    
    try:
        if db is None:
            return jsonify({"error": "Firestore not configured"}), 500
        
        body = request.json or {}
        user_id = body.get("userId")
        
        template_ref = db.collection("templates").document(template_id)
        template_doc = template_ref.get()
        
        if not template_doc.exists:
            return jsonify({"error": "Template not found"}), 404
        
        current_downloads = template_doc.to_dict().get("downloads", 0)
        template_ref.update({"downloads": current_downloads + 1})
        
        if user_id:
            users_query = db.collection("users").where("userId", "==", user_id).limit(1).stream()
            for user_doc in users_query:
                user_ref = db.collection("users").document(user_doc.id)
                user_data = user_doc.to_dict()
                current_user_downloads = user_data.get("downloadsCount", 0)
                user_ref.update({"downloadsCount": current_user_downloads + 1})
                break
        
        print(f"✅ Download tracked: Template {template_id} | User {user_id}")
        return jsonify({"message": "Download tracked", "downloads": current_downloads + 1}), 200
        
    except Exception as e:
        print(f"❌ Track download error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------- Toggle Like -----------------
@app.route("/api/users/<user_id>/likes/<template_id>", methods=["POST", "OPTIONS"])
def toggle_like(user_id, template_id):
    if request.method == "OPTIONS":
        return '', 200
    try:
        if db is None:
            return jsonify({"error": "Firestore not configured"}), 500

        users_query = db.collection("users").where("userId", "==", user_id).limit(1).stream()
        user_doc_id = None
        
        for user_doc in users_query:
            user_doc_id = user_doc.id
            break
        
        if not user_doc_id:
            return jsonify({"error": "User not found"}), 404

        user_likes_ref = db.collection("users").document(user_doc_id).collection("likes").document(template_id)
        template_ref = db.collection("templates").document(template_id)

        template = template_ref.get()
        if not template.exists:
            return jsonify({"error": "Template not found"}), 404

        user_ref = db.collection("users").document(user_doc_id)
        user_data = user_ref.get().to_dict()
        current_likes = user_data.get("likesCount", 0)

        if user_likes_ref.get().exists:
            user_likes_ref.delete()
            template_ref.update({"likes": firestore.ArrayRemove([user_id])})
            user_ref.update({"likesCount": max(0, current_likes - 1)})
            status = "unliked"
        else:
            user_likes_ref.set({"liked": True, "createdAt": now_str()})
            template_ref.update({"likes": firestore.ArrayUnion([user_id])})
            user_ref.update({"likesCount": current_likes + 1})
            status = "liked"

        updated_doc = template_ref.get().to_dict()
        likes_count = len(updated_doc.get("likes", []))
        
        print(f"✅ Like toggled: Template {template_id} | User {user_id} | Status: {status}")
        return jsonify({"status": status, "likesCount": likes_count}), 200
    except Exception as e:
        print(f"❌ Like Toggle Error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------- Dashboard Stats -----------------
@app.route("/api/dashboard", methods=["GET", "OPTIONS"])
def dashboard():
    if request.method == "OPTIONS":
        return '', 200
    try:
        if db is None:
            return jsonify({
                "totalTemplates": 0,
                "totalUsers": 0,
                "totalDownloads": 0,
                "totalLikes": 0,
                "downloadsTimeseries": [],
                "likesBreakdown": []
            }), 200

        templates = list(db.collection("templates").stream())
        users = list(db.collection("users").stream())

        total_templates = len(templates)
        total_users = len(users)
        total_downloads = 0
        total_likes = 0
        likes_breakdown = []

        for t in templates:
            data = t.to_dict() or {}
            total_downloads += data.get("downloads", 0)
            likes_count = len(data.get("likes", []))
            total_likes += likes_count
            likes_breakdown.append({"name": data.get("title", "")[:20], "value": likes_count})

        downloads_timeseries = [
            {"date": (now_utc() - timedelta(days=i)).strftime("%Y-%m-%d"),
             "downloads": total_downloads // 7 + (i * 5)}
            for i in range(6, -1, -1)
        ]

        return jsonify({
            "totalTemplates": total_templates,
            "totalUsers": total_users,
            "totalDownloads": total_downloads,
            "totalLikes": total_likes,
            "downloadsTimeseries": downloads_timeseries,
            "likesBreakdown": likes_breakdown[:10]
        }), 200
    except Exception as e:
        print(f"❌ Dashboard Error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------- Admin Stats -----------------
@app.route("/api/admin/stats", methods=["GET", "OPTIONS"])
def admin_stats():
    if request.method == "OPTIONS":
        return '', 200
    ok, admin_uid, decoded = require_admin(request)
    if not ok:
        return jsonify({"error": "Unauthorized"}), 403
    try:
        if db is None:
            return jsonify({"error": "Firestore not configured"}), 500
        
        templates_list = list(db.collection("templates").stream())
        users_list = list(db.collection("users").stream())

        total_templates = len(templates_list)
        total_users = len(users_list)
        total_downloads = 0
        total_likes = 0
        likes_breakdown = []
        category_breakdown = {}
        unique_emails = set()

        for t in templates_list:
            data = t.to_dict() or {}
            total_downloads += data.get("downloads", 0)
            likes_count = len(data.get("likes", []))
            total_likes += likes_count
            likes_breakdown.append({"name": data.get("title", "Untitled")[:20], "value": likes_count})

            cat = data.get("category", "Other")
            category_breakdown[cat] = category_breakdown.get(cat, 0) + 1

        for u in users_list:
            data = u.to_dict() or {}
            if data.get("email"):
                unique_emails.add(data["email"])

        downloads_timeseries = [
            {"date": (now_utc() - timedelta(days=i)).strftime("%Y-%m-%d"),
             "downloads": total_downloads // 7 + (i * 5)}
            for i in range(6, -1, -1)
        ]

        return jsonify({
            "totalTemplates": total_templates,
            "totalUsers": total_users,
            "totalDownloads": total_downloads,
            "totalLikes": total_likes,
            "uniqueEmails": len(unique_emails),
            "likesBreakdown": likes_breakdown[:10],
            "categoryBreakdown": [{"name": k, "value": v} for k, v in category_breakdown.items()],
            "downloadsTimeseries": downloads_timeseries
        }), 200
    except Exception as e:
        print(f"❌ Admin Stats Error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------- Admin Impersonate -----------------
@app.route("/api/admin/impersonate", methods=["POST", "OPTIONS"])
def admin_impersonate():
    if request.method == "OPTIONS":
        return '', 200
    ok, admin_uid, decoded = require_admin(request)
    if not ok:
        return jsonify({"error": "Unauthorized"}), 403
    try:
        body = request.json or {}
        email = body.get("email")
        uid = body.get("uid")

        if not email and not uid:
            return jsonify({"error": "email or uid required"}), 400

        target_uid = uid
        if email and not uid:
            try:
                user_record = firebase_auth.get_user_by_email(email)
                target_uid = user_record.uid
            except Exception:
                return jsonify({"error": "User not found"}), 404

        custom_token = firebase_auth.create_custom_token(target_uid)
        if isinstance(custom_token, bytes):
            custom_token = custom_token.decode("utf-8")
        return jsonify({"token": custom_token, "uid": target_uid}), 200
    except Exception as e:
        print(f"❌ Impersonate Error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------- Admin Force Logout -----------------
@app.route("/api/admin/force-logout", methods=["POST", "OPTIONS"])
def admin_force_logout():
    if request.method == "OPTIONS":
        return '', 200
    ok, admin_uid, decoded = require_admin(request)
    if not ok:
        return jsonify({"error": "Unauthorized"}), 403
    try:
        body = request.json or {}
        email = body.get("email")
        uid = body.get("uid")

        if not email and not uid:
            return jsonify({"error": "email or uid required"}), 400

        target_uid = uid
        if email and not uid:
            try:
                user_record = firebase_auth.get_user_by_email(email)
                target_uid = user_record.uid
            except Exception:
                return jsonify({"error": "User not found"}), 404

        firebase_auth.revoke_refresh_tokens(target_uid)
        
        if db:
            db.collection("users").document(target_uid).set({
                "isOnline": False,
                "forceLogoutAt": now_str(),
                "forceLogoutBy": admin_uid or "admin"
            }, merge=True)

        print(f"✅ User force logged out: {target_uid}")
        return jsonify({"message": "User forced to logout", "uid": target_uid}), 200
    except Exception as e:
        print(f"❌ Force Logout Error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------- Check Force Logout Status -----------------
@app.route("/api/users/<uid>/check-logout", methods=["GET", "OPTIONS"])
def check_force_logout(uid):
    if request.method == "OPTIONS":
        return '', 200
    try:
        if db is None:
            return jsonify({"forceLogout": False}), 200
        
        user_doc = db.collection("users").document(uid).get()
        if not user_doc.exists:
            return jsonify({"forceLogout": False}), 200
        
        user_data = user_doc.to_dict()
        force_logout_at = user_data.get("forceLogoutAt")
        
        if force_logout_at:
            return jsonify({"forceLogout": True, "logoutAt": force_logout_at}), 200
        
        return jsonify({"forceLogout": False}), 200
        
    except Exception as e:
        print(f"❌ Check logout error: {e}")
        return jsonify({"forceLogout": False}), 200


# ----------------- Run Server -----------------
if __name__ == "__main__":
    # Print all available routes
    print("\n" + "="*60)
    print("📋 AVAILABLE ROUTES:")
    print("="*60)
    for rule in app.url_map.iter_rules():
        methods = ','.join(rule.methods - {'HEAD', 'OPTIONS'})
        print(f"  {methods:10s} {rule.rule}")
    print("="*60 + "\n")
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)


