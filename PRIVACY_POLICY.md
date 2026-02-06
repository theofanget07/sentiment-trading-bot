# CryptoSentinel AI - Privacy Policy

**Last Updated:** February 6, 2026  
**Effective Date:** February 12, 2026

## 1. Introduction

This Privacy Policy explains how CryptoSentinel AI ("we", "our", or "the Service") collects, uses, stores, and protects your personal data when you use our Telegram-based cryptocurrency alert and analysis service.

We are committed to protecting your privacy and complying with:
- Swiss Federal Data Protection Act (FADP)
- EU General Data Protection Regulation (GDPR) (applicable when serving EU users)

**Data Controller:**  
Theo Fanget  
Rue du Crêt 7  
1003 Lausanne, Switzerland  
Telegram: @theofanget07

## 2. Data We Collect

### 2.1 Data You Provide

| Data Type | Purpose | Storage |
|-----------|---------|----------|
| **Telegram User ID** | Bot functionality (identifying your account) | Redis database |
| **Telegram Username** (optional) | Display name if you have a public username | Redis database |
| **Portfolio Positions** | Track your cryptocurrency holdings (symbols, quantities, purchase prices you manually enter) | Redis database |
| **Price Alerts** | Store your Take Profit / Stop Loss targets | Redis database |
| **Transaction History** | Record buy/sell operations you log | Redis database |
| **Subscription Status** | Track Free/Premium tier | Redis + Stripe |

### 2.2 Data We Do NOT Collect

We explicitly **DO NOT** collect:
- ❌ Full name, email, or phone number (Telegram does not provide these to bots)
- ❌ IP addresses (Telegram webhooks do not expose user IPs)
- ❌ Exchange API keys or wallet private keys
- ❌ Exact location or geolocation data
- ❌ Device identifiers (beyond Telegram's user ID)

## 3. How We Use Your Data

### 3.1 Service Provision
- Calculate portfolio Profit & Loss (P&L)
- Send automated price alert notifications when TP/SL thresholds are reached
- Generate personalized AI recommendations based on your holdings
- Deliver daily market insights (8:00 CET for Premium users)

### 3.2 Payment Processing
- Link your Telegram User ID to your Stripe Customer ID
- Verify subscription status (Free vs. Premium)
- Process recurring €9/month payments

### 3.3 Service Improvement
- Analyze aggregated usage patterns (anonymized)
- Debug technical issues
- Improve AI recommendation accuracy

## 4. Legal Basis for Processing (GDPR Article 6)

| Purpose | Legal Basis |
|---------|-------------|
| Portfolio management & alerts | **Performance of Contract** (Art. 6.1.b) - necessary to provide the service you subscribed to |
| Payment processing | **Performance of Contract** (Art. 6.1.b) |
| Service improvement | **Legitimate Interest** (Art. 6.1.f) - improving our service while respecting your rights |
| Marketing communications | **Consent** (Art. 6.1.a) - only if you opt-in (we do NOT send marketing by default) |

## 5. Data Sharing & Third-Party Processors

We share minimal data with the following trusted third-party processors:

### 5.1 CoinGecko API
- **Purpose**: Fetch real-time cryptocurrency prices
- **Data Shared**: NONE (public API, no user identifiers sent)
- **Location**: Global CDN
- **Privacy Policy**: [coingecko.com/en/privacy](https://www.coingecko.com/en/privacy)

### 5.2 Perplexity AI
- **Purpose**: Generate market sentiment analysis and trading recommendations
- **Data Shared**: Anonymized portfolio symbols only (NO Telegram IDs or personal identifiers)
- **Location**: USA (adequacy decision or Standard Contractual Clauses apply)
- **Privacy Policy**: [perplexity.ai/privacy](https://www.perplexity.ai/privacy)

### 5.3 Stripe
- **Purpose**: Payment processing for Premium subscriptions
- **Data Shared**: Telegram User ID (linked to Stripe Customer ID), subscription tier
- **Location**: EU (Stripe Payments Europe, Ltd. - Ireland)
- **Compliance**: PCI-DSS Level 1 certified, GDPR-compliant
- **Privacy Policy**: [stripe.com/privacy](https://stripe.com/privacy)

### 5.4 Railway (Infrastructure Hosting)
- **Purpose**: Host our bot backend and Redis database
- **Data Shared**: All user data stored in our database
- **Location**: **EU region (Ireland or Germany)** - GDPR-compliant
- **Privacy Policy**: [railway.app/legal/privacy](https://railway.app/legal/privacy)

**We NEVER sell your data to third parties, advertisers, or data brokers.**

## 6. Data Retention

| Data Type | Retention Period |
|-----------|------------------|
| **Active Users** | As long as your account is active OR until you request deletion |
| **Deleted Accounts** | 30 days backup retention, then permanent deletion |
| **Inactive Users** | Auto-deletion after **180 days** of inactivity (no bot interactions) |
| **Logs & Analytics** | Maximum **90 days**, then automatically purged |
| **Stripe Payment Records** | 7 years (required by Swiss/EU accounting laws) |

## 7. Your GDPR Rights

As a data subject, you have the following rights:

### 7.1 Right to Access (Art. 15 GDPR)
Request a copy of all personal data we hold about you.
- **Command**: `/mydata` - exports your data as JSON

### 7.2 Right to Erasure ("Right to be Forgotten") (Art. 17 GDPR)
Request deletion of all your personal data.
- **Command**: `/deletedata` - permanently deletes your account and data
- **Retention**: 30-day backup retention for disaster recovery, then permanent deletion

### 7.3 Right to Data Portability (Art. 20 GDPR)
Receive your data in a structured, machine-readable format.
- **Command**: `/exportdata` - downloads your data as JSON file

### 7.4 Right to Rectification (Art. 16 GDPR)
Correct inaccurate data.
- Update portfolio via `/portfolio`, `/add`, `/remove` commands
- Update alerts via `/setalert`, `/removealert`

### 7.5 Right to Object (Art. 21 GDPR)
Object to data processing based on legitimate interest.
- Use `/deletedata` to stop all processing

### 7.6 Right to Restrict Processing (Art. 18 GDPR)
Contact us via Telegram (@theofanget07) to temporarily restrict processing while disputes are resolved.

### 7.7 Right to Lodge a Complaint
**Switzerland**: [Federal Data Protection and Information Commissioner (FDPIC)](https://www.edoeb.admin.ch/)  
**EU**: Your national Data Protection Authority ([list](https://edpb.europa.eu/about-edpb/board/members_en))

## 8. Data Security

We implement industry-standard security measures:

### Technical Safeguards
- **Encryption in Transit**: All connections use HTTPS/TLS 1.3
- **Encryption at Rest**: Redis database encrypted (Railway managed)
- **Access Control**: Database accessible only via authorized backend
- **No Plain-Text Secrets**: All API keys stored as environment variables (not in code)

### Operational Safeguards
- **Daily Automated Backups** (Railway, 7-day retention)
- **Monitoring & Alerts**: Real-time error tracking (logs)
- **No Password Storage**: Authentication via Telegram (no passwords to leak)

### Limitations
No system is 100% secure. While we strive to protect your data, we cannot guarantee absolute security. In case of a data breach affecting personal data, we will:
1. Notify affected users within 72 hours (GDPR requirement)
2. Report to Swiss FDPIC / relevant EU DPA if required
3. Provide remediation steps

## 9. Cookies & Tracking

### We Do NOT Use:
- ❌ Browser cookies (Telegram bot = no web interface)
- ❌ Tracking pixels or beacons
- ❌ Third-party analytics (Google Analytics, Facebook Pixel, etc.)

### Telegram Native Tracking:
Telegram itself may collect usage data per its own Privacy Policy. We do not control Telegram's data practices.

## 10. Children's Privacy

CryptoSentinel AI is **NOT** intended for users under 18 years old. We do not knowingly collect data from minors. If we become aware of data collected from a user under 18, we will delete it immediately.

Parents/guardians: If you believe your child has used our Service, contact us for immediate account deletion.

## 11. International Data Transfers

### EU Users
When transferring data outside the EU (e.g., to Perplexity AI in the USA), we rely on:
- **Adequacy Decisions** (if available)
- **Standard Contractual Clauses (SCCs)** approved by the European Commission
- **Processor commitments** to GDPR compliance

### Swiss Users
Data transfers outside Switzerland are governed by the Swiss FADP, which recognizes EU adequacy.

## 12. Automated Decision-Making & Profiling

### AI Recommendations
Our Service uses **automated AI analysis** (Perplexity AI) to generate trading recommendations based on:
- Market sentiment (news, social media trends)
- Your portfolio composition (symbols, allocation)

**This is NOT automated decision-making with legal/significant effects** (GDPR Art. 22). You retain full control:
- You decide whether to follow recommendations
- No trades are executed automatically
- You can disable AI features anytime

### No Profiling for Marketing
We do NOT create user profiles for targeted advertising.

## 13. Changes to This Privacy Policy

We may update this Privacy Policy to reflect:
- Changes in data protection laws
- New features or data practices
- User feedback

**Notification**: We will notify users of material changes via:
- In-bot notification (sent to all active users)
- Updated GitHub repository with change log

**Your Options**:
- **Continued Use** = acceptance of changes
- **Disagree?** Cancel subscription via `/cancel` and delete data via `/deletedata`

## 14. Data Processing Agreement (DPA)

If you are a business or organization using CryptoSentinel AI on behalf of your end-users, contact us to execute a Data Processing Agreement (DPA) as required by GDPR Article 28.

## 15. Contact & Data Protection Officer (DPO)

For privacy-related questions, requests, or complaints:

**Data Controller:**  
Theo Fanget  
Telegram: @theofanget07  
GitHub: [sentiment-trading-bot](https://github.com/theofanget07/sentiment-trading-bot)

**Response Time**: We aim to respond within 30 days (GDPR requirement: 1 month, extendable to 3 months for complex requests).

**No DPO Required**: Under GDPR Art. 37, we are not required to appoint a Data Protection Officer because:
- We are not a public authority
- We do not engage in large-scale systematic monitoring
- We do not process special categories of data at scale

## 16. Consent Withdrawal

If we process your data based on **consent** (e.g., marketing emails), you can withdraw consent anytime by:
- Clicking "unsubscribe" in emails
- Contacting us via Telegram

Withdrawing consent does NOT affect:
- Processing performed before withdrawal
- Processing based on other legal grounds (contract, legitimate interest)

## 17. Swiss-Specific Provisions

### Compliance with Swiss FADP
This Privacy Policy also complies with the Swiss Federal Act on Data Protection (FADP). Swiss residents have rights equivalent to GDPR, enforceable via:
- **Federal Data Protection and Information Commissioner (FDPIC)**
- Swiss civil courts

### Cross-Border Data Flows
Data transfers to countries outside Switzerland are permitted if:
- The destination country has adequate data protection (EU = adequate)
- Standard Contractual Clauses are in place
- You have given explicit consent

## 18. Summary of Key Points

✅ **Minimal Data Collection**: Only what's necessary for the service  
✅ **No Selling**: We NEVER sell your data  
✅ **Your Control**: `/mydata`, `/deletedata`, `/exportdata` commands  
✅ **EU Hosting**: Redis database in EU region (GDPR-compliant)  
✅ **Transparent**: All data practices disclosed here  
✅ **Auto-Deletion**: Inactive accounts deleted after 180 days  

---

**By using CryptoSentinel AI, you consent to the data practices described in this Privacy Policy.**

If you have questions or wish to exercise your rights, contact us via Telegram: **@theofanget07**

**Last reviewed: February 6, 2026**
