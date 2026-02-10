from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
import redis
import os
from typing import List, Dict

router = APIRouter()

# Redis connection
redis_client = redis.from_url(os.getenv("REDIS_URL"))

# Simple token auth
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "change_me_in_production")

def verify_admin(token: str):
    """Vérifier le token admin"""
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return True

@router.get("/admin/users", response_class=HTMLResponse)
async def admin_users(request: Request, token: str = None):
    """Page de gestion des utilisateurs Premium"""
    verify_admin(token)
    
    # Récupérer tous les users depuis Redis
    users = []
    
    # Scanner tous les users (cherche les clés user:*:username)
    for key in redis_client.scan_iter("user:*:username"):
        user_id = key.decode().split(":")[1]
        username = redis_client.get(key)
        
        # Vérifier statut premium
        premium_key = f"user:{user_id}:premium"
        is_premium = redis_client.get(premium_key)
        is_premium = is_premium.decode() == "true" if is_premium else False
        
        # Récupérer subscription_id si existe
        sub_id_key = f"user:{user_id}:subscription_id"
        subscription_id = redis_client.get(sub_id_key)
        
        users.append({
            "user_id": user_id,
            "username": username.decode() if username else "Unknown",
            "is_premium": is_premium,
            "has_stripe_sub": subscription_id is not None,
            "subscription_id": subscription_id.decode()[:20] + "..." if subscription_id else None
        })
    
    # Trier : Premium en premier, puis par user_id
    users.sort(key=lambda u: (not u["is_premium"], u["user_id"]))
    
    # Stats
    total = len(users)
    premium = len([u for u in users if u["is_premium"]])
    free = total - premium
    mrr = premium * 9
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>CryptoSentinel - User Management</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #0f1419;
                color: #e7e9ea;
                padding: 30px;
            }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            
            h1 {{ 
                color: #1d9bf0; 
                margin-bottom: 10px;
                font-size: 28px;
            }}
            
            .subtitle {{
                color: #71767b;
                margin-bottom: 30px;
                font-size: 14px;
            }}
            
            /* Stats Cards */
            .stats {{
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 15px;
                margin-bottom: 30px;
            }}
            .stat-card {{
                background: #16181c;
                border: 1px solid #2f3336;
                border-radius: 12px;
                padding: 20px;
            }}
            .stat-card h3 {{
                color: #71767b;
                font-size: 13px;
                font-weight: 500;
                margin-bottom: 8px;
            }}
            .stat-card .value {{
                font-size: 32px;
                font-weight: 700;
                color: #1d9bf0;
            }}
            
            /* Search */
            .search-box {{
                margin-bottom: 20px;
            }}
            .search-box input {{
                width: 100%;
                padding: 12px 16px;
                background: #16181c;
                border: 1px solid #2f3336;
                border-radius: 8px;
                color: #e7e9ea;
                font-size: 15px;
            }}
            .search-box input::placeholder {{
                color: #71767b;
            }}
            .search-box input:focus {{
                outline: none;
                border-color: #1d9bf0;
            }}
            
            /* Table */
            .users-table {{
                background: #16181c;
                border: 1px solid #2f3336;
                border-radius: 12px;
                overflow: hidden;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
            }}
            th {{
                background: #1d1f23;
                padding: 15px;
                text-align: left;
                font-weight: 600;
                font-size: 13px;
                color: #e7e9ea;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            td {{
                padding: 15px;
                border-top: 1px solid #2f3336;
            }}
            tr:hover {{
                background: #1d1f23;
            }}
            
            /* Badges */
            .badge {{
                display: inline-block;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
            }}
            .badge-premium {{
                background: linear-gradient(135deg, #ffd700, #ffed4e);
                color: #000;
            }}
            .badge-free {{
                background: #2f3336;
                color: #71767b;
            }}
            
            /* Switch Button */
            .switch-btn {{
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 13px;
                font-weight: 600;
                transition: all 0.2s;
            }}
            .btn-premium {{
                background: linear-gradient(135deg, #1d9bf0, #0c7abf);
                color: #fff;
            }}
            .btn-free {{
                background: #2f3336;
                color: #e7e9ea;
            }}
            .switch-btn:hover {{
                opacity: 0.9;
                transform: translateY(-1px);
            }}
            
            /* Stripe indicator */
            .stripe-indicator {{
                display: inline-block;
                width: 8px;
                height: 8px;
                border-radius: 50%;
                margin-left: 8px;
            }}
            .stripe-active {{ background: #00ba7c; }}
            .stripe-inactive {{ background: #536471; }}
            
            /* User ID */
            code {{
                background: #1d1f23;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                color: #1d9bf0;
            }}
            
            /* Note */
            .note {{
                margin-top: 20px;
                padding: 15px;
                background: #16181c;
                border: 1px solid #2f3336;
                border-radius: 8px;
                color: #71767b;
                font-size: 13px;
            }}
            .note strong {{ color: #e7e9ea; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>👥 User Management</h1>
            <p class="subtitle">CryptoSentinel AI - Premium Management Dashboard</p>
            
            <!-- Stats -->
            <div class="stats">
                <div class="stat-card">
                    <h3>Total Users</h3>
                    <div class="value">{total}</div>
                </div>
                <div class="stat-card">
                    <h3>💎 Premium</h3>
                    <div class="value">{premium}</div>
                </div>
                <div class="stat-card">
                    <h3>🆓 Free</h3>
                    <div class="value">{free}</div>
                </div>
                <div class="stat-card">
                    <h3>💰 MRR</h3>
                    <div class="value">€{mrr}</div>
                </div>
            </div>
            
            <!-- Search -->
            <div class="search-box">
                <input 
                    type="text" 
                    id="searchInput" 
                    placeholder="🔍 Search by username or user ID..."
                    onkeyup="filterUsers()"
                >
            </div>
            
            <!-- Users Table -->
            <div class="users-table">
                <table id="usersTable">
                    <thead>
                        <tr>
                            <th>User ID</th>
                            <th>Username</th>
                            <th>Status</th>
                            <th>Stripe Sub</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    for user in users:
        premium_badge = '<span class="badge badge-premium">💎 PREMIUM</span>' if user["is_premium"] else '<span class="badge badge-free">🆓 FREE</span>'
        
        stripe_indicator = f'<span class="stripe-indicator stripe-active"></span>' if user["has_stripe_sub"] else '<span class="stripe-indicator stripe-inactive"></span>'
        
        subscription_info = f'<code>{user["subscription_id"]}</code>' if user["subscription_id"] else '<span style="color: #536471;">—</span>'
        
        button_text = "↓ Set FREE" if user["is_premium"] else "↑ Set PREMIUM"
        button_class = "btn-free" if user["is_premium"] else "btn-premium"
        target_status = "false" if user["is_premium"] else "true"
        
        html += f"""
                        <tr>
                            <td><code>{user["user_id"]}</code></td>
                            <td>@{user["username"]}</td>
                            <td>{premium_badge}</td>
                            <td>{subscription_info} {stripe_indicator}</td>
                            <td>
                                <button 
                                    class="switch-btn {button_class}"
                                    onclick="togglePremium('{user["user_id"]}', {target_status})"
                                >
                                    {button_text}
                                </button>
                            </td>
                        </tr>
        """
    
    html += f"""
                    </tbody>
                </table>
            </div>
            
            <div class="note">
                <strong>ℹ️ Note:</strong> 
                Les boutons "Set PREMIUM" / "Set FREE" changent uniquement le statut dans Redis (accès aux features du bot).
                <br><br>
                <strong>Pour gérer les paiements Stripe</strong> (remboursements, annulations, invoices) → 
                <a href="https://dashboard.stripe.com/subscriptions" target="_blank" style="color: #1d9bf0;">Stripe Dashboard</a>
                <br><br>
                🟢 = Abonnement Stripe actif | ⚫ = Pas d'abonnement Stripe (Premium manuel)
            </div>
        </div>
        
        <script>
            const token = new URLSearchParams(window.location.search).get('token');
            
            // Search filter
            function filterUsers() {{
                const input = document.getElementById('searchInput');
                const filter = input.value.toLowerCase();
                const table = document.getElementById('usersTable');
                const rows = table.getElementsByTagName('tr');
                
                for (let i = 1; i < rows.length; i++) {{
                    const row = rows[i];
                    const text = row.textContent.toLowerCase();
                    row.style.display = text.includes(filter) ? '' : 'none';
                }}
            }}
            
            // Toggle Premium status
            async function togglePremium(userId, setPremium) {{
                const action = setPremium ? 'PREMIUM' : 'FREE';
                
                if (!confirm(`Set user ${{userId}} to ${{action}}?`)) return;
                
                try {{
                    const res = await fetch(`/admin/toggle-premium/${{userId}}?token=${{token}}&premium=${{setPremium}}`, {{
                        method: 'POST'
                    }});
                    
                    if (res.ok) {{
                        const data = await res.json();
                        alert(`✅ ${{data.message}}`);
                        location.reload();
                    }} else {{
                        const error = await res.json();
                        alert(`❌ Error: ${{error.detail}}`);
                    }}
                }} catch (e) {{
                    alert(`❌ Network error: ${{e.message}}`);
                }}
            }}
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html)

@router.post("/admin/toggle-premium/{user_id}")
async def toggle_premium(user_id: str, token: str, premium: bool):
    """Switch user entre FREE et PREMIUM"""
    verify_admin(token)
    
    # Update Redis
    key = f"user:{user_id}:premium"
    redis_client.set(key, "true" if premium else "false")
    
    return {
        "success": True,
        "user_id": user_id,
        "premium": premium,
        "message": f"User {user_id} set to {'PREMIUM' if premium else 'FREE'}"
    }
