from io import BytesIO
from datetime import datetime
import re
import zipfile
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

NAVY="#0F172A"; BLUE="#2563EB"; CYAN="#06B6D4"; GREEN="#22C55E"; RED="#EF4444"; GRAY="#64748B"; LIGHT="#F8FAFC"; PURPLE="#7C3AED"


def safe(value):
    return str(value or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")


def metric(metrics,key,default=0):
    try:
        return max(0,min(100,int(metrics.get(key,default))))
    except Exception:
        return default


def parse_sections(reply):
    titles=["Overview","Pros","Cons","Target Market","Revenue Model","TAM / SAM / SOM","Competitor Intelligence","SWOT Analysis","Financial Feasibility","Funding Recommendation","Market Signals","Business Model Canvas","Improvement Suggestions","Execution Roadmap","AI Co-Founder Questions","A/B Comparison","Funding Needed","Final Score"]
    pattern=r"(?im)^\s*("+"|".join(re.escape(t) for t in titles)+r")\s*:\s*$"
    matches=list(re.finditer(pattern,reply or ""))
    if not matches:
        return [{"title":"Startup Analysis","items":[],"paragraphs":[reply or ""]}]
    sections=[]
    for i,m in enumerate(matches):
        body=(reply[m.end():matches[i+1].start() if i+1<len(matches) else len(reply)]).strip()
        items=[]; paras=[]
        for line in body.splitlines():
            line=line.strip()
            if not line: continue
            if line.startswith('- '): items.append(line[2:])
            else: paras.append(line)
        sections.append({"title":m.group(1),"items":items,"paragraphs":paras})
    return sections


def build_pdf_report(idea, reply, metrics=None, user_email="", structured=None):
    metrics=metrics or {}; structured=structured or {}; sections=parse_sections(reply)
    buf=BytesIO(); doc=SimpleDocTemplate(buf,pagesize=A4,rightMargin=40,leftMargin=40,topMargin=42,bottomMargin=42,title="AI Startup Feasibility Analysis")
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='CoverTitle',parent=styles['Title'],fontName='Times-Bold',fontSize=28,leading=34,textColor=colors.HexColor(NAVY),alignment=TA_CENTER,spaceAfter=14))
    styles.add(ParagraphStyle(name='Sub',parent=styles['BodyText'],fontName='Times-Roman',fontSize=11,leading=16,textColor=colors.HexColor(GRAY),alignment=TA_CENTER,spaceAfter=14))
    styles.add(ParagraphStyle(name='Heading',parent=styles['Heading2'],fontName='Times-Bold',fontSize=15,leading=18,textColor=colors.HexColor(BLUE),spaceBefore=14,spaceAfter=6))
    styles.add(ParagraphStyle(name='Clean',parent=styles['BodyText'],fontName='Times-Roman',fontSize=10.2,leading=15,textColor=colors.HexColor(NAVY),spaceAfter=5))
    story=[Spacer(1,.45*inch),Paragraph("AI Startup Feasibility Analyzer",styles['CoverTitle']),Paragraph("Professional business analysis, investor readiness and feasibility report",styles['Sub'])]
    meta=[["Startup Idea",Paragraph(safe(idea),styles['Clean'])],["Generated For",safe(user_email)],["Generated On",datetime.now().strftime('%d %B %Y, %I:%M %p')]]
    t=Table(meta,colWidths=[1.35*inch,4.75*inch]); t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#EEF2FF')),('TEXTCOLOR',(0,0),(0,-1),colors.HexColor(BLUE)),('FONTNAME',(0,0),(0,-1),'Times-Bold'),('BOX',(0,0),(-1,-1),1,colors.HexColor('#CBD5E1')),('INNERGRID',(0,0),(-1,-1),.5,colors.HexColor('#CBD5E1')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)])); story.append(t); story.append(Spacer(1,.3*inch))
    mdata=[["Success","Investor Ready","Market","Risk"],[f"{metric(metrics,'success_probability',50)}%",f"{metric(metrics,'investor_readiness',60)}%",f"{metric(metrics,'market_potential',60)}%",f"{metric(metrics,'competition_risk',40)}%"]]
    mt=Table(mdata,colWidths=[1.5*inch]*4); mt.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor(NAVY)),('TEXTCOLOR',(0,0),(-1,0),colors.white),('BACKGROUND',(0,1),(-1,1),colors.HexColor('#F8FAFC')),('FONTNAME',(0,0),(-1,-1),'Times-Bold'),('FONTSIZE',(0,1),(-1,1),20),('ALIGN',(0,0),(-1,-1),'CENTER'),('BOX',(0,0),(-1,-1),1,colors.HexColor('#CBD5E1')),('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10)])); story.append(mt); story.append(PageBreak())
    story.append(Paragraph("Detailed Feasibility Analysis",styles['CoverTitle']))
    for sec in sections:
        story.append(Paragraph(safe(sec['title']),styles['Heading']))
        for p in sec['paragraphs']: story.append(Paragraph(safe(p),styles['Clean']))
        for item in sec['items']: story.append(Paragraph('• '+safe(item),styles['Clean']))
    story.append(Spacer(1,.2*inch)); story.append(Paragraph("Generated by AI Startup Feasibility Analyzer",styles['Sub']))
    def footer(canvas,doc_obj):
        canvas.saveState(); canvas.setStrokeColor(colors.HexColor('#CBD5E1')); canvas.line(40,32,A4[0]-40,32); canvas.setFont('Times-Roman',8); canvas.setFillColor(colors.HexColor(GRAY)); canvas.drawString(40,20,'AI Startup Feasibility Analyzer'); canvas.drawRightString(A4[0]-40,20,f'Page {doc_obj.page}'); canvas.restoreState()
    doc.build(story,onFirstPage=footer,onLaterPages=footer); buf.seek(0); return buf


# Pure standard-library PPTX writer. This avoids python-pptx runtime/export failures.
SLIDE_W = 12192000
SLIDE_H = 6858000

def emu(inches):
    return int(inches * 914400)


def clean_text(text, limit=900):
    text = re.sub(r'\s+', ' ', str(text or '')).strip()
    return text[:limit] + ('...' if len(text) > limit else '')


def bullet_lines(items, limit=6):
    out=[]
    for item in items or []:
        if isinstance(item, dict):
            item = '; '.join(f"{k}: {v}" for k,v in item.items() if v)
        out.append(clean_text(item, 170))
        if len(out) >= limit: break
    return out or ['Information will appear after analysis.']


def tx_shape(idx, x, y, w, h, text, size=2200, bold=False, color='0F172A', fill=None, line='D8E2F0'):
    runs = []
    lines = str(text or '').split('\n')
    for n, line_text in enumerate(lines):
        safe_line = escape(line_text)
        b = '<a:b/>' if bold else ''
        runs.append(f'<a:p><a:r><a:rPr lang="en-US" sz="{size}">{b}<a:solidFill><a:srgbClr val="{color}"/></a:solidFill><a:latin typeface="Times New Roman"/></a:rPr><a:t>{safe_line}</a:t></a:r></a:p>')
    fill_xml = f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>' if fill else '<a:noFill/>'
    line_xml = f'<a:ln><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln>' if line else '<a:ln><a:noFill/></a:ln>'
    return f'''<p:sp><p:nvSpPr><p:cNvPr id="{idx}" name="TextBox {idx}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm><a:prstGeom prst="roundRect"><a:avLst/></a:prstGeom>{fill_xml}{line_xml}</p:spPr><p:txBody><a:bodyPr wrap="square" lIns="130000" tIns="90000" rIns="130000" bIns="90000"/><a:lstStyle/>{''.join(runs)}</p:txBody></p:sp>'''


def slide_xml(shapes):
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="F8FAFC"/></a:solidFill><a:effectLst/></p:bgPr></p:bg><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>{''.join(shapes)}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>'''


def make_slide(title, subtitle='', boxes=None, cover=False):
    shapes=[]; idx=2
    if cover:
        shapes.append(tx_shape(idx, emu(.65), emu(1.35), emu(11.5), emu(1.0), title, 4200, True, '0F172A')); idx+=1
        shapes.append(tx_shape(idx, emu(.72), emu(2.55), emu(10.8), emu(.7), subtitle, 2000, False, '64748B')); idx+=1
        shapes.append(tx_shape(idx, emu(.72), emu(4.65), emu(4.6), emu(.65), 'AI Startup Feasibility Analyzer', 1800, True, 'FFFFFF', '2563EB', '2563EB')); idx+=1
    else:
        shapes.append(tx_shape(idx, emu(.48), emu(.28), emu(12.0), emu(.55), title, 2800, True, '0F172A')); idx+=1
        if subtitle:
            shapes.append(tx_shape(idx, emu(.52), emu(.86), emu(12.0), emu(.38), subtitle, 1300, False, '64748B')); idx+=1
        for b in boxes or []:
            heading=b.get('heading','')
            body=b.get('body','')
            text = heading + ('\n' if heading and body else '') + body
            shapes.append(tx_shape(idx, emu(b.get('x',.7)), emu(b.get('y',1.35)), emu(b.get('w',5.8)), emu(b.get('h',2.0)), text, b.get('size',1300), False, b.get('color','0F172A'), 'FFFFFF', 'D8E2F0')); idx+=1
    return slide_xml(shapes)


def pct_line(label, val):
    return f"{label}: {val}%"


def build_ppt_report(idea, reply, metrics=None, user_email="", structured=None):
    metrics=metrics or {}; structured=structured or {}
    title = structured.get('title','Startup Feasibility Analysis')
    overview = structured.get('overview','')
    pros = '\n'.join('• '+x for x in bullet_lines(structured.get('pros'),5))
    cons = '\n'.join('• '+x for x in bullet_lines(structured.get('cons'),5))
    risks = '\n'.join('• '+x for x in bullet_lines(structured.get('risks'),5))
    roadmap = '\n'.join('• '+x for x in bullet_lines(structured.get('roadmap'),6))
    questions = '\n'.join('• '+x for x in bullet_lines(structured.get('cofounder_questions'),5))
    tam=structured.get('tam_sam_som',{}) or {}
    sw=structured.get('swot',{}) or {}
    fin=structured.get('financial_projection',{}) or {}
    fund=structured.get('funding_recommendation',{}) or {}
    comp=structured.get('competitors',[]) or []
    comp_lines='\n'.join('• '+clean_text(f"{c.get('name','Competitor')}: {c.get('opportunity','Opportunity')}",160) for c in comp[:4]) or '• Competitor details will appear after analysis.'
    comparison=structured.get('comparison') or {}
    comp_score=''
    if comparison:
        a=comparison.get('idea_a') or {}; b=comparison.get('idea_b') or {}
        comp_score=f"Idea A Score: {a.get('score','--')}/10\nIdea B Score: {b.get('score','--')}/10\nWinner: {comparison.get('winner','--')}\nDecision: {comparison.get('decision','')}"

    slides=[]
    slides.append(make_slide('AI Startup Feasibility Analysis', f'{title} | Generated for {user_email or "User"} | {datetime.now().strftime("%d %b %Y")}', cover=True))
    slides.append(make_slide('Executive Scorecard', title, [
        {'x':.55,'y':1.35,'w':3.0,'h':1.5,'heading':'Success Probability','body':pct_line('Success',metric(metrics,'success_probability',60)),'color':'16A34A','size':1500},
        {'x':3.85,'y':1.35,'w':3.0,'h':1.5,'heading':'Market Potential','body':pct_line('Market',metric(metrics,'market_potential',60)),'color':'2563EB','size':1500},
        {'x':7.15,'y':1.35,'w':3.0,'h':1.5,'heading':'Investor Readiness','body':pct_line('Investor',metric(metrics,'investor_readiness',60)),'color':'7C3AED','size':1500},
        {'x':.55,'y':3.25,'w':5.95,'h':2.65,'heading':'Business Description','body':clean_text(overview,650),'size':1250},
        {'x':6.85,'y':3.25,'w':5.95,'h':2.65,'heading':'Investment & Funding','body':clean_text(structured.get('funding_needed_text','')+' '+fund.get('best_path','')+' '+fund.get('estimated_seed_need',''),620),'size':1250},
    ]))
    slides.append(make_slide('Success, Failure and Risk View', 'Balanced decision-making snapshot', [
        {'x':.55,'y':1.35,'w':3.85,'h':2.25,'heading':'Success Drivers','body':pros,'color':'16A34A','size':1150},
        {'x':4.75,'y':1.35,'w':3.85,'h':2.25,'heading':'Failure Possibilities','body':cons,'color':'DC2626','size':1150},
        {'x':8.95,'y':1.35,'w':3.75,'h':2.25,'heading':'Key Risks','body':risks,'color':'F59E0B','size':1150},
        {'x':.55,'y':4.05,'w':5.9,'h':1.75,'heading':'Prerequisites','body':clean_text('Clear target niche, validated demand, MVP, basic budget, reliable API access, user feedback, and marketing channel testing.',420),'size':1200},
        {'x':6.85,'y':4.05,'w':5.85,'h':1.75,'heading':'Risk Scores','body':f"Competition Risk: {metric(metrics,'competition_risk',40)}%\nFinancial Risk: {metric(metrics,'financial_risk',40)}%\nExecution Complexity: {metric(metrics,'execution_complexity',50)}%",'size':1200},
    ]))
    slides.append(make_slide('Market, Competitors and SWOT', 'Where the startup can win', [
        {'x':.55,'y':1.35,'w':3.85,'h':2.05,'heading':'TAM / SAM / SOM','body':clean_text('TAM: '+tam.get('tam','')+'\nSAM: '+tam.get('sam','')+'\nSOM: '+tam.get('som',''),520),'size':1050},
        {'x':4.75,'y':1.35,'w':3.85,'h':2.05,'heading':'Competitor Gaps','body':comp_lines,'color':'7C3AED','size':1050},
        {'x':8.95,'y':1.35,'w':3.75,'h':2.05,'heading':'SWOT Snapshot','body':clean_text('Strengths: '+', '.join(sw.get('strengths',[])[:3])+'\nOpportunities: '+', '.join(sw.get('opportunities',[])[:3]),480),'color':'2563EB','size':1050},
        {'x':.55,'y':3.85,'w':5.9,'h':1.95,'heading':'Revenue Model','body':clean_text(structured.get('revenue_model',''),430),'size':1150},
        {'x':6.85,'y':3.85,'w':5.85,'h':1.95,'heading':'A/B Comparison Scores','body':comp_score or 'Use A/B Compare to generate different scores for both ideas.','size':1150},
    ]))
    slides.append(make_slide('Roadmap and AI Co-Founder Guidance', 'Practical next steps', [
        {'x':.55,'y':1.35,'w':5.9,'h':3.9,'heading':'Execution Roadmap','body':roadmap,'color':'2563EB','size':1200},
        {'x':6.85,'y':1.35,'w':5.85,'h':3.9,'heading':'Questions to Validate','body':questions,'color':'7C3AED','size':1200},
        {'x':.55,'y':5.55,'w':12.15,'h':.75,'heading':'Final Score','body':f"{structured.get('final_score','--')}/10 | {structured.get('voice_summary','')}",'color':'16A34A','size':1200},
    ]))
    return pptx_package(slides)


def pptx_package(slides):
    buf=BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', content_types(len(slides)))
        z.writestr('_rels/.rels', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/></Relationships>''')
        z.writestr('ppt/presentation.xml', presentation_xml(len(slides)))
        z.writestr('ppt/_rels/presentation.xml.rels', presentation_rels(len(slides)))
        for i,xml in enumerate(slides,1):
            z.writestr(f'ppt/slides/slide{i}.xml', xml)
        z.writestr('ppt/theme/theme1.xml', theme_xml())
        z.writestr('ppt/slideMasters/slideMaster1.xml', master_xml())
        z.writestr('ppt/slideMasters/_rels/slideMaster1.xml.rels', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/></Relationships>''')
        z.writestr('ppt/slideLayouts/slideLayout1.xml', layout_xml())
        z.writestr('ppt/slideLayouts/_rels/slideLayout1.xml.rels', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/></Relationships>''')
        z.writestr('docProps/core.xml', f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>AI Startup Feasibility Analysis</dc:title><dc:creator>AI Startup Analyzer</dc:creator><cp:lastModifiedBy>AI Startup Analyzer</cp:lastModifiedBy><dcterms:created xsi:type="dcterms:W3CDTF">{datetime.utcnow().isoformat()}Z</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">{datetime.utcnow().isoformat()}Z</dcterms:modified></cp:coreProperties>''')
        z.writestr('docProps/app.xml', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>AI Startup Analyzer</Application><PresentationFormat>Widescreen</PresentationFormat><Slides>5</Slides></Properties>''')
    buf.seek(0); return buf


def content_types(n):
    overrides=''.join(f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>' for i in range(1,n+1))
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/><Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/><Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/><Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>{overrides}<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/><Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/></Types>'''


def presentation_xml(n):
    ids=''.join(f'<p:sldId id="{255+i}" r:id="rId{i}"/>' for i in range(1,n+1))
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId{n+1}"/></p:sldMasterIdLst><p:sldIdLst>{ids}</p:sldIdLst><p:sldSz cx="{SLIDE_W}" cy="{SLIDE_H}" type="wide"/><p:notesSz cx="6858000" cy="9144000"/><p:defaultTextStyle/></p:presentation>'''


def presentation_rels(n):
    rels=''.join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>' for i in range(1,n+1))
    rels+=f'<Relationship Id="rId{n+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>'
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{rels}</Relationships>'''


def theme_xml():
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Office Theme"><a:themeElements><a:clrScheme name="Office"><a:dk1><a:srgbClr val="000000"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="1F2937"/></a:dk2><a:lt2><a:srgbClr val="F8FAFC"/></a:lt2><a:accent1><a:srgbClr val="2563EB"/></a:accent1><a:accent2><a:srgbClr val="06B6D4"/></a:accent2><a:accent3><a:srgbClr val="22C55E"/></a:accent3><a:accent4><a:srgbClr val="7C3AED"/></a:accent4><a:accent5><a:srgbClr val="EF4444"/></a:accent5><a:accent6><a:srgbClr val="F59E0B"/></a:accent6><a:hlink><a:srgbClr val="2563EB"/></a:hlink><a:folHlink><a:srgbClr val="7C3AED"/></a:folHlink></a:clrScheme><a:fontScheme name="Office"><a:majorFont><a:latin typeface="Times New Roman"/></a:majorFont><a:minorFont><a:latin typeface="Times New Roman"/></a:minorFont></a:fontScheme><a:fmtScheme name="Office"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="6350"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme></a:themeElements></a:theme>'''


def master_xml():
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld><p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/><p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId2"/></p:sldLayoutIdLst><p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles></p:sldMaster>'''


def layout_xml():
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1"><p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>'''
