#!/usr/bin/env python3
"""Produce image-based, one-at-a-time CEEC Chinese exam questions.

Uses original CEEC PDFs (not AI recreations). Do not treat automatic cropping as
human-verified: shared reading passages, figures, column flow and page breaks
MUST be checked at assets/chinese/review.html.
"""
from __future__ import annotations
import html
import json
import re
import sys
import time
from pathlib import Path
import fitz
import requests
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
SOURCES=json.loads((ROOT/'official-sources.json').read_text('utf8'))
DEST=ROOT/'assets'/'chinese'
NUM=re.compile(r'^\s*(\d{1,2})\s*[.．、]\s*\S')
GROUP=re.compile(r'(\d{1,2})\s*[-～~—至－]\s*(\d{1,2})\s*為題組')
OFFICIAL_115={1:'C',2:'A',3:'D',4:'B',5:'C',6:'D',7:'C',8:'D',9:'A',10:'C',11:'D',12:'B',13:'B',14:'B',15:'A',16:'D',17:'B',18:'D',19:'D',20:'A',21:'A',22:'C',23:'B',24:'C',25:'BE',26:'ABD',27:'ABD',28:'ACDE',29:'CD',30:'CD',31:'ABE',35:'C',36:'A'}

def download_pdf(url:str)->bytes:
    ss=requests.Session();ss.headers.update({'User-Agent':'Mozilla/5.0 GSAT-Chinese-study/1.0','Accept':'application/pdf,*/*'})
    last=None
    for attempt in range(3):
        try:
            r=ss.get(url,timeout=70);r.raise_for_status()
            if not r.content.startswith(b'%PDF-'):raise RuntimeError(f'expected PDF; got {r.headers.get("Content-Type")}')
            return r.content
        except Exception as exc:
            last=exc;time.sleep(attempt+1)
    raise RuntimeError(f'Download failed: {last}')

def lines(page):
    out=[]
    for block in page.get_text('dict',sort=True)['blocks']:
        if block.get('type')!=0:continue
        for line in block.get('lines',[]):
            spans=line['spans'];txt=''.join(s['text'] for s in spans).strip()
            if not txt:continue
            out.append((min(sp['bbox'][0] for sp in spans),min(sp['bbox'][1] for sp in spans),txt))
    return sorted(out,key=lambda p:(p[1],p[0]))

def docpos(doc,loc):return sum(p.rect.height for p in list(doc)[:loc[0]])+loc[1]

def identify(doc):
    candidates={n:[] for n in range(1,61)};groups=[]
    for pi,page in enumerate(doc):
        for x,y,t in lines(page):
            if y<45 or y>page.rect.height-43:continue
            m=NUM.match(t)
            if x<145 and m:
                n=int(m.group(1))
                if n in candidates:candidates[n].append((pi,y,x,t))
            g=GROUP.search(t)
            if g and x<180:groups.append((int(g.group(1)),int(g.group(2)),(pi,y,x,t)))
    anchors={};previous=-1
    for n in range(1,61):
        eligible=[p for p in candidates[n] if docpos(doc,p)>previous+10]
        if not eligible:
            # A single missing marker must not hide every later question.
            continue
        # Earlier, left-aligned matching line is the safer default; preserve doubt in review.
        start=min(eligible,key=lambda p:(docpos(doc,p),max(0,p[2]-90)*.1))
        anchors[n]=start;previous=docpos(doc,start)
    return anchors,groups

def render_segment(doc,start,end,dpi=134):
    if docpos(doc,end)<=docpos(doc,start)+9:return None
    parts=[]
    for pi in range(start[0],end[0]+1):
        page=doc[pi]
        top=(start[1]-6) if pi==start[0] else 46
        bottom=(end[1]-7) if pi==end[0] else page.rect.height-42
        top=max(43,top);bottom=min(page.rect.height-40,bottom)
        if bottom<top+12:continue
        pix=page.get_pixmap(matrix=fitz.Matrix(dpi/72,dpi/72),clip=fitz.Rect(49,top,page.rect.width-40,bottom),alpha=False)
        parts.append(Image.frombytes('RGB',(pix.width,pix.height),pix.samples))
    if not parts:return None
    if len(parts)==1:return parts[0]
    wide=max(p.width for p in parts)
    img=Image.new('RGB',(wide,sum(p.height for p in parts)+8*(len(parts)-1)),'white')
    y=0
    for p in parts:img.paste(p,(0,y));y+=p.height+8
    return img

def parse_keys(data:bytes):
    """Parse x/y table cell pairs, fail closed if ambiguous."""
    doc=fitz.open(stream=data,filetype='pdf');observed={};nonchoice=set()
    for page in doc:
        words=page.get_text('words',sort=True)
        rows=[]
        for w in words:
            found=None
            for row in rows:
                if abs(row[0]-w[1])<4.5:found=row;break
            if found is None:found=[w[1],[]];rows.append(found)
            found[1].append((w[0],w[4].strip()))
        for _,cells in rows:
            toks=[(x,t.replace('（','').replace('）','').replace('、','').replace('.','')) for x,t in sorted(cells)]
            for i,(x,t) in enumerate(toks):
                if not re.fullmatch(r'\d{1,2}',t):continue
                n=int(t)
                if n<1 or n>60:continue
                for _,candidate in toks[i+1:i+5]:
                    key=re.sub(r'[^A-E／/]','',candidate.upper())
                    if key and re.fullmatch(r'[A-E]{1,5}|[／/]',key):
                        if key in ('／','/'):nonchoice.add(n)
                        else:observed.setdefault(n,[]).append(''.join(sorted(set(key))))
                        break
    # Drop a number whose possible answers disagree; never make a guess.
    clean={str(n):keys[0] for n,keys in observed.items() if keys and len(set(keys))==1}
    doc.close();return clean,nonchoice

def save_image(img,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    img.save(path,format='WEBP',quality=84,method=5)

def process(year,urls):
    image_pdf=download_pdf(urls['exam']);doc=fitz.open(stream=image_pdf,filetype='pdf')
    anchors,groups=identify(doc)
    out={};shared={}
    # Before a new passage-based question group, stop the previous question there.
    for start_n,end_n,pos in groups:
        anchor=anchors.get(start_n)
        if anchor and docpos(doc,pos)<docpos(doc,anchor)-8:
            img=render_segment(doc,pos,anchor)
            if img and img.height>=65:
                path=DEST/str(year)/f'group_{start_n:02}_{end_n:02}.webp'
                save_image(img,path)
                for n in range(start_n,end_n+1):shared[n]=f'assets/chinese/{year}/{path.name}'
    for n,loc in sorted(anchors.items()):
        nxt=anchors.get(n+1)
        if not nxt:
            # Avoid speculative massive extraction if the next marker isn't found.
            if n!=max(anchors):continue
            nxt=(loc[0],doc[loc[0]].rect.height-45,0,'end')
        if docpos(doc,nxt)<=docpos(doc,loc):continue
        end=nxt
        if n+1 in shared:
            matches=[pos for a,b,pos in groups if a==n+1 and docpos(doc,loc)<docpos(doc,pos)<docpos(doc,nxt)]
            if matches:end=min(matches,key=lambda p:docpos(doc,p))
        img=render_segment(doc,loc,end)
        if img is None or img.height<75:continue
        path=DEST/str(year)/f'q{n:02}.webp'
        save_image(img,path)
        out[str(n)]={'image':f'assets/chinese/{year}/{path.name}', 'page':loc[0]+1,'size':[img.width,img.height]}
        if n in shared:out[str(n)]['shared']=shared[n]
    doc.close()
    try:keys,nonchoice=parse_keys(download_pdf(urls['ans']))
    except Exception as e:print(f'WARNING {year} answers unavailable: {e}',flush=True);keys={};nonchoice=set()
    if int(year)==115:
        keys.update({str(n):v for n,v in OFFICIAL_115.items()})
        nonchoice.update((32,33,34))
    for n in list(keys):
        if str(n) not in out and n not in ('1','2','3'):continue
    review='\n'.join(f'q{n} PDF page {m["page"]} [{m["size"]}]{" (shared passage)" if m.get("shared") else ""}' for n,m in out.items())
    (DEST/str(year)/'quality-check.txt').write_text(review,'utf8')
    print(f'{year}: extracted {len(out)} original question images, {len(keys)} trusted answer keys, shared passages {len(shared)}',flush=True)
    types={str(n):'non' for n in nonchoice}
    types.update({n:'multi' if len(a)>1 else 'single' for n,a in keys.items()})
    return out,keys,types

def build_review(manifest):
    cards=[]
    for y,paper in manifest['papers'].items():
        for q,v in paper.items():
            if v.get('shared'):cards.append(f'<article><b>{y} 年第 {q} 題 · 共用題組</b><img src="{html.escape(v["shared"].removeprefix("assets/chinese/"))}"></article>')
            cards.append(f'<article><b>{y} 年第 {q} 題 · 第 {v["page"]} 頁</b><img src="{html.escape(v["image"].removeprefix("assets/chinese/"))}"></article>')
    page='<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>國文逐題圖片核對</title><style>body{background:#f3f6ef;font-family:system-ui;max-width:980px;margin:auto;padding:20px}article{background:#fff;padding:15px;margin:18px 0;border-radius:12px}img{display:block;max-width:100%;height:auto}b{display:block;margin-bottom:15px}</style><h1>國文官方原題逐題圖片核對表</h1><p>請人工核對每題是否完整，特別是閱讀題組共用文章、跨頁、插圖、非選擇題。自動切圖不等同人工校對。</p>'+''.join(cards)+'</html>'
    (DEST/'review.html').write_text(page,'utf8')

def main():
    DEST.mkdir(parents=True,exist_ok=True)
    manifest={'schema':1,'source':'CEEC official PDF; machine-generated image crops; manual review required','papers':{},'answers':{},'types':{}}
    failures=[]
    for year in sorted(SOURCES,reverse=True):
        try:
            images,answers,types=process(year,SOURCES[year]);manifest['papers'][year]=images;manifest['answers'][year]=answers;manifest['types'][year]=types
        except Exception as e:failures.append(f'{year}: {e}');print('ERROR',failures[-1],file=sys.stderr,flush=True)
    (DEST/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n','utf8');build_review(manifest)
    num=sum(len(v) for v in manifest['papers'].values())
    print(f'Generated {num} question images across {len(manifest["papers"])} years. Review assets/chinese/review.html',flush=True)
    if failures:print('Some years failed:',*failures,sep='\n',file=sys.stderr)
    if not num:sys.exit(1)
if __name__=='__main__':main()
