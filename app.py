import json
import os
import re
from datetime import datetime
from io import BytesIO

from flask import Flask, request, jsonify, render_template, redirect, url_for, send_file
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from groq import Groq

from models import db, User, Message, AnalysisReport
from export_utils import build_pdf_report, build_ppt_report

try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None
try:
    from docx import Document
except Exception:
    Document = None

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-before-deployment")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

ALLOWED_EXTENSIONS = {"txt", "pdf", "docx"}

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")
    return Groq(api_key=api_key) if api_key else None


def extract_json(raw_text):
    raw_text = (raw_text or "").strip()
    try:
        return json.loads(raw_text)
    except Exception:
        match = re.search(r"\{.*\}", raw_text, flags=re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def safe_list(value, fallback=None):
    return value if isinstance(value, list) and value else (fallback or [])


def clamp(value, default=0):
    try:
        return int(max(0, min(100, float(value))))
    except Exception:
        return default


def user_memory_context():
    if not current_user.is_authenticated:
        return ""
    reports = AnalysisReport.query.filter_by(user_id=current_user.id).order_by(AnalysisReport.created_at.desc()).limit(5).all()
    if not reports:
        return "No previous startup analyses yet."
    lines = [f"- {r.title}: {r.idea[:150]}" for r in reports]
    return "Previous startup ideas analyzed for this user:\n" + "\n".join(lines)


def fallback_analysis(idea, mode="full", second_idea=""):
    title = (idea[:58].strip().title() or "Startup Idea")
    success = 72 if len(idea) > 35 else 64
    competition = 42
    execution = 54
    financial = 39
    structured = {
        "title": title,
        "overview": f"This startup idea has practical potential if it targets a clear niche, validates demand early, and launches a simple MVP before scaling. Idea: {idea}",
        "pros": ["Solves a clear business/user problem", "Can be launched as an MVP", "AI can create differentiation and automation", "Good scope for scalable SaaS-style growth"],
        "cons": ["Market validation is still required", "Customer acquisition cost may be uncertain", "Execution quality strongly affects success", "Competition may copy features quickly"],
        "target_market": "Early adopters, students, startup founders, small businesses, incubators, and users who need quick decision support.",
        "revenue_model": "Freemium plan, monthly subscriptions, paid premium reports, professional PPT exports, B2B licensing, and consulting support.",
        "risks": ["Competitors may already have strong brand trust", "Users may not pay unless ROI is clear", "API and hosting cost can increase with usage", "Weak data validation can reduce confidence"],
        "funding_needed_text": "Moderate funding is needed for product development, cloud hosting, API usage, marketing, and customer support.",
        "final_score": 7.4,
        "metrics": {
            "success_probability": success,
            "losing_probability": 100 - success,
            "funds_required": 44,
            "market_potential": 78,
            "competition_risk": competition,
            "financial_risk": financial,
            "execution_complexity": execution,
            "innovation_score": 76,
            "investor_readiness": 70,
            "mvp_readiness": 74,
            "scalability_score": 77
        },
        "competitors": [
            {"name": "Generic AI Chatbots", "strength": "Flexible responses", "weakness": "Not domain-specific", "opportunity": "Provide structured feasibility dashboards and exports"},
            {"name": "Business Consultants", "strength": "Expert judgement", "weakness": "Expensive and slow", "opportunity": "Offer fast and affordable first-level analysis"},
            {"name": "Startup Planning Tools", "strength": "Templates and frameworks", "weakness": "Limited AI personalization", "opportunity": "Combine AI analysis with visual reports"}
        ],
        "tam_sam_som": {
            "tam": "Large global market of founders, students, incubators, and small businesses needing startup planning and validation.",
            "sam": "Reachable online users in the selected region/language who need affordable AI business analysis.",
            "som": "Initial obtainable market can be one college ecosystem, startup community, or small founder niche."
        },
        "business_model_canvas": {
            "value_proposition": "Fast AI-powered startup feasibility, risk analysis, dashboards, and investor-ready exports.",
            "customer_segments": "Students, founders, small businesses, incubators, and early-stage teams.",
            "channels": "Website, social media, startup communities, colleges, referrals, and incubators.",
            "revenue_streams": "Subscriptions, premium reports, PPT reports, B2B plans, and consulting.",
            "key_activities": "AI analysis, report generation, dashboard visualization, user onboarding, and prompt improvement.",
            "key_resources": "Groq API, Flask backend, database, export engine, UI, and business analysis prompts.",
            "key_partners": "Colleges, startup mentors, incubators, API providers, and cloud platforms.",
            "cost_structure": "API usage, hosting, database, design, marketing, maintenance, and support."
        },
        "swot": {
            "strengths": ["Fast analysis", "Low-cost digital delivery", "Good presentation/export value"],
            "weaknesses": ["Needs better real-world data validation", "Depends on prompt quality"],
            "opportunities": ["Can target colleges/incubators", "Can become B2B startup planning tool"],
            "threats": ["Generic AI tools", "Consultants and existing SaaS platforms"]
        },
        "financial_projection": {
            "assumptions": "Freemium acquisition with paid subscriptions and export-based premium plans.",
            "month_1_revenue": "₹5,000 - ₹15,000",
            "month_6_revenue": "₹60,000 - ₹1,50,000",
            "break_even_estimate": "4-8 months if marketing and API costs remain controlled",
            "profitability_note": "Profitability improves when templates, exports, and repeat users reduce manual effort."
        },
        "funding_recommendation": {
            "best_path": "Bootstrap first, then approach angel investors after traction.",
            "estimated_seed_need": "₹1 lakh - ₹5 lakh for MVP, API usage, hosting, and marketing.",
            "when_to_raise": "After 100+ active users, testimonials, and early paid conversions."
        },
        "roadmap": ["Validate idea with 20 target users", "Build MVP landing page", "Launch beta", "Track conversion and retention", "Improve pricing and exports", "Approach mentors/investors"],
        "improvements": ["Start with one clear niche", "Add real user feedback", "Show quantified dashboards", "Add trust-building examples", "Use simple pricing"],
        "market_signals": [
            {"signal": "AI adoption", "status": "Positive", "meaning": "Users are increasingly comfortable with AI-assisted productivity tools."},
            {"signal": "SaaS willingness", "status": "Moderate", "meaning": "Users pay when the product clearly saves time or money."},
            {"signal": "Competition", "status": "Medium", "meaning": "Differentiation through reports, dashboards, and PPT reports is important."}
        ],
        "presentation_outline": {
            "problem": "Users need fast, affordable, structured startup validation before investing time and money.",
            "solution": "An AI-powered platform that generates feasibility reports, dashboards, SWOT, roadmap, and PPT reports.",
            "market": "Students, founders, incubators, and small businesses looking for decision support.",
            "product": "Chat-based analyzer with metrics, exports, idea comparison, and AI co-founder suggestions.",
            "business_model": "Freemium + premium exports + subscriptions + B2B licensing.",
            "go_to_market": "College startup cells, LinkedIn content, founder communities, and referral-based growth.",
            "ask": "Funding/support for API credits, hosting, UI polish, marketing, and customer validation."
        },
        "cofounder_questions": ["Who exactly feels this problem most urgently?", "What proof shows they will pay?", "What feature can be launched in 7 days?", "Why should users choose this over ChatGPT?", "What metric will prove traction?"],
        "voice_summary": "This startup has good potential if it validates demand early, focuses on one niche, and proves users are willing to pay."
    }
    if mode == "compare" and second_idea:
        structured["title"] = "A/B Startup Idea Comparison"
        structured["overview"] = f"Idea A and Idea B were compared on market potential, risk, monetization, execution complexity, and investor readiness. Idea A: {idea}. Idea B: {second_idea}."
        structured["comparison"] = {
            "idea_a": {"name": idea[:80], "score": 7.4, "reason": "Better if it has a clear target market and low MVP complexity."},
            "idea_b": {"name": second_idea[:80], "score": 7.0, "reason": "Good alternative, but may require more validation or stronger differentiation."},
            "winner": "Idea A",
            "decision": "Choose the idea that can be validated fastest with real users and lowest initial cost."
        }
    return structured


def normalize_structured(data, idea, mode="full", second_idea=""):
    base = fallback_analysis(idea, mode, second_idea)
    if not isinstance(data, dict):
        return base
    merged = {**base, **data}
    merged["metrics"] = {**base["metrics"], **(data.get("metrics") if isinstance(data.get("metrics"), dict) else {})}
    for key in ["pros", "cons", "risks", "competitors", "roadmap", "improvements", "market_signals", "cofounder_questions"]:
        merged[key] = safe_list(data.get(key), base[key])
    for key, default in base["metrics"].items():
        merged["metrics"][key] = clamp(merged["metrics"].get(key), default)
    merged["metrics"]["losing_probability"] = 100 - merged["metrics"].get("success_probability", 65)
    try:
        merged["final_score"] = round(max(0, min(10, float(merged.get("final_score", 7)))), 1)
    except Exception:
        merged["final_score"] = base["final_score"]
    return merged


def make_reply(data):
    comp = data.get("competitors", [])
    canvas = data.get("business_model_canvas", {})
    tam = data.get("tam_sam_som", {})
    swot = data.get("swot", {})
    fin = data.get("financial_projection", {})
    fund = data.get("funding_recommendation", {})
    signals = data.get("market_signals", [])
    comparison = data.get("comparison")

    lines = [
        "Overview:", data.get("overview", ""), "",
        "Pros:", *[f"- {x}" for x in data.get("pros", [])], "",
        "Cons:", *[f"- {x}" for x in data.get("cons", [])], "",
        "Target Market:", data.get("target_market", ""), "",
        "Revenue Model:", data.get("revenue_model", ""), "",
        "TAM / SAM / SOM:", f"- TAM: {tam.get('tam','')}", f"- SAM: {tam.get('sam','')}", f"- SOM: {tam.get('som','')}", "",
        "Competitor Intelligence:", *[f"- {c.get('name','Competitor')}: Strength - {c.get('strength','N/A')}; Weakness - {c.get('weakness','N/A')}; Opportunity - {c.get('opportunity','N/A')}" for c in comp], "",
        "SWOT Analysis:",
        f"- Strengths: {', '.join(swot.get('strengths', []))}",
        f"- Weaknesses: {', '.join(swot.get('weaknesses', []))}",
        f"- Opportunities: {', '.join(swot.get('opportunities', []))}",
        f"- Threats: {', '.join(swot.get('threats', []))}", "",
        "Financial Feasibility:", *[f"- {k.replace('_',' ').title()}: {v}" for k, v in fin.items()], "",
        "Funding Recommendation:", *[f"- {k.replace('_',' ').title()}: {v}" for k, v in fund.items()], "",
        "Market Signals:", *[f"- {s.get('signal','Signal')}: {s.get('status','')} - {s.get('meaning','')}" for s in signals], "",
        "Business Model Canvas:", *[f"- {k.replace('_',' ').title()}: {v}" for k, v in canvas.items()], "",
        "Improvement Suggestions:", *[f"- {x}" for x in data.get("improvements", [])], "",
        "Execution Roadmap:", *[f"- {x}" for x in data.get("roadmap", [])], "",
        "AI Co-Founder Questions:", *[f"- {x}" for x in data.get("cofounder_questions", [])], "",
    ]
    if comparison:
        lines += ["A/B Comparison:", f"- Winner: {comparison.get('winner')}", f"- Decision: {comparison.get('decision')}", ""]
    lines += ["Funding Needed:", data.get("funding_needed_text", ""), "", "Final Score:", f"{data.get('final_score',0)}/10"]
    return "\n".join(lines)


def analyze_startup(idea, mode="full", second_idea="", extra_context=""):
    client = get_groq_client()
    if not client:
        structured = fallback_analysis(idea, mode, second_idea)
        return {"reply": make_reply(structured), "metrics": structured["metrics"], "structured": structured}

    prompt = f"""
You are an expert startup analyst, investor, product strategist, business feasibility consultant, and AI co-founder.
Analyze the startup idea deeply and return ONLY valid JSON. No markdown.

User memory context:
{user_memory_context()}

Extra uploaded document context:
{extra_context[:2500]}

Mode: {mode}
Startup Idea A: {idea}
Startup Idea B if comparison mode: {second_idea}

Return this JSON structure exactly:
{{
 "title":"short title",
 "overview":"impressive summary",
 "pros":["..."], "cons":["..."],
 "target_market":"specific audience", "revenue_model":"earning methods",
 "risks":["..."], "funding_needed_text":"funding explanation", "final_score":7.5,
 "metrics":{{"success_probability":72,"losing_probability":28,"funds_required":40,"market_potential":78,"competition_risk":45,"financial_risk":38,"execution_complexity":55,"innovation_score":74,"investor_readiness":70,"mvp_readiness":75,"scalability_score":76}},
 "competitors":[{{"name":"...","strength":"...","weakness":"...","opportunity":"..."}}],
 "tam_sam_som":{{"tam":"...","sam":"...","som":"..."}},
 "business_model_canvas":{{"value_proposition":"...","customer_segments":"...","channels":"...","revenue_streams":"...","key_activities":"...","key_resources":"...","key_partners":"...","cost_structure":"..."}},
 "swot":{{"strengths":["..."],"weaknesses":["..."],"opportunities":["..."],"threats":["..."]}},
 "financial_projection":{{"assumptions":"...","month_1_revenue":"...","month_6_revenue":"...","break_even_estimate":"...","profitability_note":"..."}},
 "funding_recommendation":{{"best_path":"...","estimated_seed_need":"...","when_to_raise":"..."}},
 "roadmap":["month/step ..."], "improvements":["..."],
 "market_signals":[{{"signal":"...","status":"Positive/Moderate/Risky","meaning":"..."}}],
 "presentation_outline":{{"problem":"...","solution":"...","market":"...","product":"...","business_model":"...","go_to_market":"...","ask":"..."}},
 "cofounder_questions":["hard question ..."],
 "voice_summary":"one short spoken summary",
 "comparison":{{"idea_a":{{"name":"...","score":7.2,"reason":"..."}},"idea_b":{{"name":"...","score":7.0,"reason":"..."}},"winner":"Idea A/Idea B","decision":"..."}}
}}
Rules: metric values must be 0-100. If not comparison mode, still include comparison with empty/null reasonable values.
"""
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.35,
            top_p=0.9,
        )
        raw = response.choices[0].message.content.strip()
        structured = normalize_structured(extract_json(raw), idea, mode, second_idea)
    except Exception:
        structured = fallback_analysis(idea, mode, second_idea)
    return {"reply": make_reply(structured), "metrics": structured["metrics"], "structured": structured}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_uploaded_text(file_storage):
    name = secure_filename(file_storage.filename or "")
    ext = name.rsplit(".", 1)[-1].lower()
    data = file_storage.read()
    if ext == "txt":
        return data.decode("utf-8", errors="ignore")
    if ext == "pdf" and PdfReader:
        reader = PdfReader(BytesIO(data))
        return "\n".join([(p.extract_text() or "") for p in reader.pages])
    if ext == "docx" and Document:
        doc = Document(BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)
    return ""


@app.route("/")
def index():
    return redirect(url_for("home")) if current_user.is_authenticated else redirect(url_for("login"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "").strip()
        if not email or not phone or not password:
            return render_template("signup.html", error="Please fill all fields.")
        if User.query.filter_by(email=email).first():
            return render_template("signup.html", error="This email is already registered. Please login.")
        new_user = User(email=email, phone=phone, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("home"))
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        user = User.query.filter_by(email=email).first()
        if not user:
            return render_template("login.html", error="No account found with this email.")
        if not check_password_hash(user.password, password):
            return render_template("login.html", error="Incorrect password.")
        login_user(user)
        return redirect(url_for("home"))
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/home")
@login_required
def home():
    return render_template("index.html", user_email=current_user.email)


@app.route("/admin")
@login_required
def admin():
    if current_user.id != 1:
        return redirect(url_for("home"))
    users = User.query.order_by(User.created_at.desc()).all()
    reports = AnalysisReport.query.order_by(AnalysisReport.created_at.desc()).limit(100).all()
    return render_template("admin.html", users=users, reports=reports)


def save_report(idea, result):
    reply, metrics, structured = result["reply"], result["metrics"], result["structured"]
    db.session.add(Message(user_id=current_user.id, sender="user", content=idea))
    db.session.add(Message(user_id=current_user.id, sender="bot", content=reply))
    report = AnalysisReport(user_id=current_user.id, idea=idea, title=structured.get("title", "Startup Analysis"), reply=reply, metrics_json=json.dumps(metrics), structured_json=json.dumps(structured))
    db.session.add(report)
    db.session.commit()
    return report


@app.route("/chat", methods=["POST"])
@login_required
def chat():
    data = request.json or {}
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "Please enter a startup idea."}), 400
    result = analyze_startup(user_message)
    report = save_report(user_message, result)
    return jsonify({**result, "report_id": report.id})


@app.route("/compare", methods=["POST"])
@login_required
def compare():
    data = request.json or {}
    idea_a = data.get("idea_a", "").strip()
    idea_b = data.get("idea_b", "").strip()
    if not idea_a or not idea_b:
        return jsonify({"error": "Please enter both startup ideas."}), 400
    combined = f"Idea A: {idea_a}\nIdea B: {idea_b}"
    result = analyze_startup(idea_a, mode="compare", second_idea=idea_b)
    report = save_report(combined, result)
    return jsonify({**result, "report_id": report.id})


@app.route("/api/upload-business-plan", methods=["POST"])
@login_required
def upload_business_plan():
    idea = request.form.get("idea", "Uploaded business plan analysis").strip()
    f = request.files.get("file")
    if not f or not allowed_file(f.filename):
        return jsonify({"error": "Upload a .txt, .pdf, or .docx business plan."}), 400
    extracted = extract_uploaded_text(f)
    if not extracted.strip():
        return jsonify({"error": "Could not read text from this file."}), 400
    result = analyze_startup(idea, extra_context=extracted)
    report = save_report(idea, result)
    return jsonify({**result, "report_id": report.id})


@app.route("/api/reports")
@login_required
def list_reports():
    reports = AnalysisReport.query.filter_by(user_id=current_user.id).order_by(AnalysisReport.created_at.desc()).limit(30).all()
    return jsonify([r.to_dict() for r in reports])


@app.route("/api/reports/<int:report_id>")
@login_required
def get_report(report_id):
    report = AnalysisReport.query.filter_by(id=report_id, user_id=current_user.id).first_or_404()
    return jsonify(report.to_dict())


def report_payload_from_request():
    data = request.get_json(silent=True) or {}
    report_id = data.get("report_id")
    if report_id:
        report = AnalysisReport.query.filter_by(id=report_id, user_id=current_user.id).first()
        if report:
            return report.idea, report.reply, report.metrics, report.structured
    return data.get("idea", ""), data.get("reply", ""), data.get("metrics", {}), data.get("structured", {})


@app.route("/export/pdf", methods=["POST"])
@login_required
def export_pdf():
    idea, reply, metrics, structured = report_payload_from_request()
    if not reply:
        return jsonify({"error": "No analysis found to export."}), 400
    buf = build_pdf_report(idea, reply, metrics, current_user.email, structured)
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name="startup_feasibility_analysis.pdf")


@app.route("/export/ppt", methods=["POST"])
@login_required
def export_ppt():
    idea, reply, metrics, structured = report_payload_from_request()
    if not reply:
        return jsonify({"error": "No analysis found to export."}), 400
    buf = build_ppt_report(idea, reply, metrics, current_user.email, structured)
    return send_file(buf, mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation", as_attachment=True, download_name="startup_feasibility_presentation.pptx")




with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
