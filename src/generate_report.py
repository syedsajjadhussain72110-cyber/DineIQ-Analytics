"""Generate a usable PDF/JSON result from independently verified outputs."""
import json
from datetime import datetime,timezone
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
from src.database import ROOT
from src.workflow import source_digest,requirements,record_stage

def generate(root=ROOT):
    source=source_digest(root);dependencies=requirements('generate',root)
    def read(n):return json.loads((root/f'reports/{n}.json').read_text(encoding='utf-8'))
    summary,comparison,py,spark=[read(n) for n in ['summary','comparison','python_models','spark_models']]
    result={'generated_at':datetime.now(timezone.utc).isoformat(),'team':'Vision AI','source_sha256':source,'synthetic':True,'currency':'PKR','summary':summary,'comparison':comparison,'models':{'python':py['selected'],'spark':spark['selected']},'evaluation':{'python':py['models'][py['selected']]['test'],'spark':spark['models'][spark['selected']]['test']},'limitations':['Synthetic evaluation data; no real restaurant outcomes are claimed.','Contribution excludes overhead and is not accounting profit.','Model agreement is not accuracy. Forecasts are estimates.'],'files':{'report':'Generated_Result_Report.pdf','comparison':'comparison.csv'}}
    regular,bold='Helvetica','Helvetica-Bold'
    rf=root/'static/fonts/DejaVuSans.ttf';bf=root/'static/fonts/DejaVuSans-Bold.ttf'
    if rf.exists() and bf.exists():
        pdfmetrics.registerFont(TTFont('DineIQ',str(rf)));pdfmetrics.registerFont(TTFont('DineIQ-Bold',str(bf)));regular,bold='DineIQ','DineIQ-Bold'
    styles=getSampleStyleSheet()
    for style in styles.byName.values():style.fontName=bold if 'Heading' in style.name else regular
    styles.add(ParagraphStyle(name='Brand',fontName=bold,fontSize=25,leading=30,textColor=colors.HexColor('#29251f'),spaceAfter=10))
    styles['BodyText'].fontSize=9.5;styles['BodyText'].leading=13;styles['BodyText'].spaceAfter=6
    content=[Paragraph('DineIQ Analytics',styles['Brand']),Paragraph('VERIFIED PIPELINE RESULT | VISION AI',styles['Heading2']),Paragraph('Independent model evidence and restaurant business context.',styles['BodyText']),Paragraph('Generated UTC: '+escape(result['generated_at']),styles['BodyText']),Spacer(1,8)]
    def section(title,rows):
        content.append(Paragraph(title,styles['Heading2']))
        data=[[Paragraph(escape(str(a)),styles['BodyText']),Paragraph(escape(str(b)),styles['BodyText'])] for a,b in rows]
        t=Table(data,colWidths=[195,310],hAlign='LEFT');t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(0,-1),colors.HexColor('#f4eee3')),('LINEBELOW',(0,0),(-1,-1),.5,colors.HexColor('#ded8cd')),('LEFTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),4)]));content.extend([t,Spacer(1,10)])
    section('01 / Business snapshot',[('Period',f"{summary['start_date']} to {summary['end_date']}"),('Net revenue',f"PKR {summary['revenue']:,.2f}"),('Contribution before overhead',f"PKR {summary['contribution']:,.2f}"),('Recorded waste cost',f"PKR {summary['waste_cost']:,.2f}"),('Completed orders',f"{summary['orders']:,}"),('Quality-checked lines',f"{summary['fact_rows']:,}")])
    section('02 / Independent model evaluation',[('Python selected model',py['selected']),('Spark selected model',spark['selected']),('Python test RMSE',f"{result['evaluation']['python']['rmse']:.4f}"),('Spark test RMSE',f"{result['evaluation']['spark']['rmse']:.4f}"),('Equivalent unseen cases',comparison['cases']),('Agreement at declared tolerance',f"{comparison['agreement_pct']:.2f}% at {comparison['tolerance']:.2%}"),('Cases requiring review',comparison['disagreements'])])
    content.extend([Paragraph('03 / What to do next',styles['Heading2']),Paragraph('Investigate high-volume low-margin dishes in Menu intelligence. Review waste and preparation plans before changing stock. Compare both model errors against actual demand before selecting an operational forecasting approach.',styles['BodyText']),Paragraph('Evidence and limits',styles['Heading2'])])
    for text in result['limitations']:content.append(Paragraph(escape(text),styles['BodyText']))
    content.append(Paragraph('Source SHA-256: '+source,styles['Code']))
    path=root/'reports/Generated_Result_Report.pdf';path.parent.mkdir(exist_ok=True);temp=path.with_suffix('.pdf.tmp')
    def footer(canvas,doc):
        canvas.setFont(regular,8);canvas.setFillColor(colors.HexColor('#756c60'));canvas.drawString(45,28,'DineIQ Analytics / Vision AI / Synthetic evaluation');canvas.drawRightString(550,28,str(doc.page))
    SimpleDocTemplate(str(temp),pagesize=(595,842),leftMargin=45,rightMargin=45,topMargin=38,bottomMargin=45,title='DineIQ Verified Pipeline Result',author='Vision AI').build(content,onFirstPage=footer,onLaterPages=footer)
    temp.replace(path);(root/'reports/generated_result.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
    record_stage('generate',source,dependencies,root)
    print(json.dumps({'status':'completed','report':str(path),'cases':comparison['cases']}),flush=True);return result
if __name__=='__main__':generate()
