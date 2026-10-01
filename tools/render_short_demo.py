"""Build the illustrated explainer from synthetic results and native captures.

Build-only dependencies: Pillow, imageio-ffmpeg. English voice is synthesized
locally using Windows Speech, not a recording of the maintainer.
"""
from pathlib import Path
from collections import Counter
import hashlib
import json
import math
import subprocess
import textwrap
import wave
import zipfile

from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/short-demo-060';DELIVERY=OUT/'delivery'
DELIVERY.mkdir(parents=True,exist_ok=True)
W,H,FPS=1280,720,20
BG,INK,TEAL,AMBER,MUTED='#f3f2ed','#18313e','#167a75','#be633b','#627379'
FONTS=Path('C:/Windows/Fonts')
def font(size,bold=False,zh=False):
    return ImageFont.truetype(str(FONTS/('msyh.ttc' if zh else 'segoeuib.ttf' if bold else 'segoeui.ttf')),size)
FT,FS,FC,FL,FN,FZH=font(43,True),font(23),font(28,True),font(19),font(68,True),font(23,zh=True)
SCENES=[
 {'title':'Follow a batch','zh':'把检验、偏差和措施连起来','seconds':9,
  'voice':'BatchScope connects a batch to its tests, deviations, and follow-up actions. Start with the records, then follow their links.'},
 {'title':'Review the change','zh':'谁改了什么？为什么修改？','seconds':10,
  'voice':'In this fictional log, a test value changes from ninety-nine to ninety-eight. The change reason is blank. That record needs a closer look.'},
 {'title':'Flags are questions','zh':'标记是复核线索，不是违规结论','seconds':10,
  'voice':'Other rules check configured permissions and working hours. A late-night operation is context, not proof of a violation. You can inspect the original event.'},
 {'title':'Compare several dates','zh':'不只看两个日期，沿时间线看变化','seconds':12,
  'voice':'Choose up to twelve dates. Each point uses the same input snapshot. Here, open deviations fall in July, while overdue actions continue to rise.'},
 {'title':'Explain the difference','zh':'查看新增与解除，不只看总数','seconds':10,
  'voice':'The overdue total moves from thirty to thirty-three. Four actions become overdue, and one is resolved. The movement table shows which records changed.'},
 {'title':'Open the evidence','zh':'搜索事件，再查看原始操作','seconds':10,
  'voice':'Search by user, event, rule, or batch. Open a finding to see its original values and policy. These pictures show the actual desktop application.'},
 {'title':'Keep the full report','zh':'保留数据、规则和中英文报告','seconds':9,
  'voice':'Export the full results to SQLite, CSV, JSON, and English or Chinese reports. Everything stays local. Try the included example in the Windows download.'},
]
data=json.loads((OUT/'quality-timeline.json').read_text(encoding='utf-8'))
rows=data['rows']
changes=Counter(r['change'] for r in data['actions'] if r['from_date']=='2026-06-30')
assert changes['newly_overdue']==4 and changes['resolved_overdue']==1
assert [r['overdue_actions'] for r in rows][-2:]==[30,33]

def prepare_audio():
    (OUT/'scenes.json').write_text(json.dumps(SCENES,ensure_ascii=False,indent=2),encoding='utf-8-sig')
    ps=OUT/'narrate.ps1'
    ps.write_text('''param([string]$Folder)
Add-Type -AssemblyName System.Speech
$ErrorActionPreference = 'Stop'
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
$speaker.SelectVoice("Microsoft Zira Desktop")
$speaker.Rate = 1
$scenes = Get-Content -LiteralPath (Join-Path $Folder 'scenes.json') -Raw -Encoding UTF8 | ConvertFrom-Json
for ($i=0; $i -lt $scenes.Count; $i++) {
    $speaker.SetOutputToWaveFile((Join-Path $Folder ("voice-" + $i + ".wav")))
    $speaker.Speak($scenes[$i].voice)
    $speaker.SetOutputToNull()
}
$speaker.Dispose()
''',encoding='utf-8-sig')
    commands="$Folder = '"+str(OUT).replace("'", "''")+"'\n"+ps.read_text(encoding='utf-8-sig').split('\n',1)[1]
    subprocess.run(['powershell','-NoProfile','-Command',commands],check=True)
    blocks=[];params=None;cursor=0
    for i,scene in enumerate(SCENES):
        with wave.open(str(OUT/f'voice-{i}.wav')) as wav:
            p=wav.getparams();params=params or p
            assert (p.nchannels,p.sampwidth,p.framerate)==(params.nchannels,params.sampwidth,params.framerate)
            audio=wav.readframes(wav.getnframes())
            seconds=p.nframes/p.framerate
        scene['seconds']=max(scene['seconds'],math.ceil(seconds+1))
        scene['start']=cursor;cursor+=scene['seconds'];scene['end']=cursor
        unit=params.nchannels*params.sampwidth
        lead=bytes(round(.35*params.framerate)*unit)
        total=round(scene['seconds']*params.framerate)*unit
        blocks.append(lead+audio+bytes(total-len(lead)-len(audio)))
    with wave.open(str(DELIVERY/'BatchScope-Short-Narration.wav'),'wb') as target:
        target.setnchannels(params.nchannels);target.setsampwidth(params.sampwidth);target.setframerate(params.framerate)
        target.writeframes(b''.join(blocks))
    return cursor

def smooth(x):
    x=max(0,min(1,x));return x*x*(3-2*x)

def txt(d,xy,text,f=FC,color=INK):d.text(xy,text,font=f,fill=color)
def card(d,x,y,w,h,title,sub='',color=TEAL):
    d.rounded_rectangle((x,y,x+w,y+h),radius=18,fill='#ffffff',outline='#d8e1dc',width=2)
    d.rounded_rectangle((x+16,y+18,x+22,y+h-18),radius=3,fill=color)
    txt(d,(x+38,y+21),title)
    if sub:txt(d,(x+38,y+63),sub,FS,MUTED)
def arrow(d,x,y,end,color=TEAL):
    d.line((x,y,end,y),fill=color,width=4)
    d.polygon([(end,y),(end-12,y-7),(end-12,y+7)],fill=color)

captures={key:Image.open(ROOT/'docs/screenshots'/filename).convert('RGB') for key,filename in
          [('audit','audit-review-en.png'),('timeline','multi-date-en.png')]}

def frame(index,t,seconds):
    scene=SCENES[index];im=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(im)
    txt(d,(64,25),'BATCHSCOPE  /  0.6',FL,TEAL)
    txt(d,(64,61),scene['title'],FT)
    txt(d,(66,119),scene['zh'],FZH,MUTED)
    progress=smooth(t/1.5)
    if index==0:
        card(d,75,260,260,150,'Batch B0001','Synthetic batch')
        for j,(title,sub) in enumerate([('Test result','Measurement'),('Deviation','Case record'),('Action','Follow-up')]):
            y=190+j*125;reveal=smooth((t-.4*j)/1.2)
            x=650+round((1-reveal)*330)
            if reveal>0:
                d.line((335,330,555,330,555,y+50,x,y+50),fill='#92b6ad',width=3)
                card(d,x,y,420,104,title,sub)
        # A moving marker follows the link, rather than a static process diagram.
        px=360+180*((t*.3)%1);d.ellipse((px-7,323,px+7,337),fill=AMBER)
    elif index==1:
        x=80+round((1-progress)*-400)
        card(d,x,220,1120,245,'E002 · QC · 11:00 UTC','Test result changed')
        txt(d,(x+55,322),'99',FN,MUTED);arrow(d,x+170,362,x+345)
        txt(d,(x+385,322),'98',FN,TEAL)
        d.rounded_rectangle((x+640,317,x+1070,421),radius=12,fill='#fcf0dd',outline=AMBER,width=2)
        txt(d,(x+668,335),'Change reason',FS,AMBER);txt(d,(x+668,370),'[ blank ]',FC,INK)
        radius=28+6*math.sin(t*3)
        d.ellipse((x+1034-radius,262-radius,x+1034+radius,262+radius),outline=AMBER,width=3)
        txt(d,(x+1017,242),'?',FC,AMBER)
    elif index==2:
        for j,(title,sub) in enumerate([('Reason missing','Check the explanation'),('Permission mismatch','Check the configured role'),('Outside working hours','Check the context')]):
            reveal=smooth((t-j*.65)/1.3);y=210+j*110+round((1-reveal)*45)
            if reveal>0:card(d,80,y,740,95,title,sub,AMBER if j<2 else TEAL)
        d.ellipse((925,245,1125,445),fill='#ffffff',outline=TEAL,width=5)
        angle=t*.5;cx,cy=1025,345
        d.line((cx,cy,cx+52*math.sin(angle),cy-52*math.cos(angle)),fill=TEAL,width=6)
        d.line((cx,cy,cx-40,cy),fill=INK,width=6)
        txt(d,(899,472),'Review, then decide',FS,TEAL)
    elif index==3:
        left,right,top,bottom=115,1150,210,475
        d.line((left,top,left,bottom,right,bottom),fill='#b3c3be',width=2)
        for val in (0,10,20,30):txt(d,(66,bottom-val*7),str(val),FL,MUTED)
        for j,(key,color,label) in enumerate([('open_deviations',TEAL,'Open deviations'),('overdue_actions',AMBER,'Overdue actions')]):
            txt(d,(110+j*390,175),label,FS,color)
            points=[(left+i*(right-left)/3,bottom-row[key]*7) for i,row in enumerate(rows)]
            amount=min(3,max(0,(t-.6)*.65))
            for i in range(3):
                part=max(0,min(1,amount-i))
                if part:
                    a,b=points[i],points[i+1]
                    d.line((*a,a[0]+(b[0]-a[0])*part,a[1]+(b[1]-a[1])*part),fill=color,width=5)
            for i,(x,y) in enumerate(points):
                if amount>=i:
                    d.ellipse((x-7,y-7,x+7,y+7),fill=color)
                    txt(d,(x-17,y-36),str(rows[i][key]),FS,color)
        for i,row in enumerate(rows):txt(d,(left+i*(right-left)/3-43,493),row['date'][5:],FS,MUTED)
    elif index==4:
        card(d,80,210,330,285,'30','June 30')
        txt(d,(117,329),'Overdue',FT,AMBER)
        card(d,870,210,330,285,'33','July 31')
        txt(d,(907,329),'Overdue',FT,AMBER)
        arrow(d,410,354,866)
        for y,title,color in [(242,'+4 newly overdue',AMBER),(404,'−1 resolved',TEAL)]:
            x=450+round(8*math.sin(t*1.2))
            d.rounded_rectangle((x,y,x+350,y+85),radius=14,fill='#fff',outline=color,width=3)
            txt(d,(x+23,y+22),title,FC,color)
    elif index==5:
        shot=captures['audit'].crop((20,115,captures['audit'].width-20,720))
        shot.thumbnail((1095,365))
        im.paste(shot,(92,178))
        d=ImageDraw.Draw(im)
        alpha=3+round(2*(1+math.sin(t*2)))
        d.rounded_rectangle((87,175,1193,544),radius=14,outline=TEAL,width=alpha)
        card(d,795,205,360,290,'E002','Source evidence')
        txt(d,(833,310),'99 → 98',FT,TEAL)
        txt(d,(833,375),'Reason: blank',FS,AMBER)
        txt(d,(833,424),'Illustrated detail',FL,MUTED)
        txt(d,(94,557),'Actual desktop capture · fictional input',FL,MUTED)
    else:
        for j,(title,sub) in enumerate([('SQLite','Events + findings'),('CSV / JSON','Full evidence'),('EN / 中文','Offline reports')]):
            x=80+j*405;offset=round(50*(1-smooth((t-j*.4)/1.3)))
            card(d,x,222+offset,365,165,title,sub)
        txt(d,(82,441),'Local files. No paid API.',FT,TEAL)
        txt(d,(84,500),'github.com/rayexzh/batchscope',FS,INK)
    # Readable bilingual chapter captions; speech text is supplied separately as SRT.
    d.rectangle((0,600,W,720),fill=INK)
    lines=textwrap.wrap(scene['voice'],width=95)
    # Reveal short narration chunks in time with each chapter.
    chunks=[lines[i:i+2] for i in range(0,len(lines),2)]
    chunk=chunks[min(len(chunks)-1,int(t/seconds*len(chunks)))]
    for i,line in enumerate(chunk):txt(d,(64,615+i*30),line,FS,'#ffffff')
    txt(d,(64,687),'Synthetic data · illustrated explainer · synthesized English voice',FL,'#abc2c7')
    width=round((scene['start']+t)/TOTAL*W)
    d.rectangle((0,596,width,600),fill='#61c5ad')
    return im

def stamp(seconds):
    ms=round(seconds*1000)
    return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}'

if __name__=='__main__':
    TOTAL=prepare_audio();assert 60<=TOTAL<=100
    subtitles=[]
    for scene in SCENES:
        parts=textwrap.wrap(scene['voice'],95)
        groups=[' '.join(parts[i:i+2]) for i in range(0,len(parts),2)]
        for i,part in enumerate(groups):
            subtitles.append((scene['start']+scene['seconds']*i/len(groups),scene['start']+scene['seconds']*(i+1)/len(groups),part))
    (DELIVERY/'BatchScope-Short-Subtitles.srt').write_text('\n\n'.join(f'{i+1}\n{stamp(a)} --> {stamp(b)}\n{text}' for i,(a,b,text) in enumerate(subtitles))+'\n',encoding='utf-8')
    script='# BatchScope short explainer / 短动画演示\n\nIllustrated synthetic-data explanation with native desktop captures and synthesized Microsoft Zira narration. Not an uninterrupted screen recording or the maintainer speaking. / 模拟数据动画，含真实软件截图和本机合成旁白，不是连续录屏或作者本人录音。\n\n'
    script+='\n\n'.join(f'## {scene["title"]} / {scene["zh"]}\n\n{scene["voice"]}' for scene in SCENES)
    (ROOT/'docs/demo/SHORT_SCRIPT.md').write_text(script+'\n',encoding='utf-8')
    ffmpeg=imageio_ffmpeg.get_ffmpeg_exe();video=DELIVERY/'BatchScope-Short-Explainer.mp4'
    with (OUT/'encoding.log').open('w') as log:
        process=subprocess.Popen([ffmpeg,'-y','-hide_banner','-loglevel','warning','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','pipe:0','-i',str(DELIVERY/'BatchScope-Short-Narration.wav'),'-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-af','loudnorm=I=-16:TP=-1.5:LRA=11','-c:a','aac','-b:a','128k','-movflags','+faststart','-t',str(TOTAL),str(video)],stdin=subprocess.PIPE,stderr=log)
        for index,scene in enumerate(SCENES):
            for i in range(round(scene['seconds']*FPS)):
                process.stdin.write(frame(index,i/FPS,scene['seconds']).tobytes())
            frame(index,scene['seconds']*.65,scene['seconds']).save(OUT/f'preview-{index}.png')
            print(f'Encoded chapter {index+1}/{len(SCENES)}',flush=True)
        process.stdin.close()
        if process.wait()!=0:raise RuntimeError('Encoding failed; inspect encoding.log')
    subprocess.run([ffmpeg,'-v','error','-i',str(video),'-f','null','-'],check=True)
    # Extract representative encoded frames, not only rendering previews.
    for seconds in (25,37,54):
        subprocess.run([ffmpeg,'-y','-loglevel','error','-ss',str(seconds),'-i',str(video),'-frames:v','1',str(OUT/f'encoded-{seconds}.png')],check=True)
    manifest={'version':'0.6.0-alpha.1','seconds':TOTAL,'resolution':[W,H],'fps':FPS,
              'format':'H.264/AAC MP4','voice':'Microsoft Zira Desktop, local synthesized English',
              'chapters':SCENES,'data':'fixed-seed synthetic BatchScope inputs',
              'full_decode':'passed','sha256':hashlib.sha256(video.read_bytes()).hexdigest()}
    (DELIVERY/'VIDEO_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    with zipfile.ZipFile(OUT/'BatchScope-Short-Demo-Pack.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(DELIVERY.iterdir()):archive.write(p,p.name)
        archive.write(ROOT/'docs/demo/SHORT_SCRIPT.md','SHORT_SCRIPT.md')
    print(json.dumps({'video':str(video),'seconds':TOTAL,'bytes':video.stat().st_size,'decode':'passed'}),flush=True)
