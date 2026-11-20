#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每日专注力挑战视频生成器: 圆盘/小球/短时记忆, 无答案揭晓.
Usage: python scripts/generate.py --day 4 --output-dir output/DAY04
Dependencies: Pillow numpy shapely; ffmpeg on PATH.
"""
from __future__ import annotations
import argparse, json, math, random, subprocess, wave, zipfile, shutil, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
PALETTE = ['#DCEBF2','#E7E4F6','#E2F0DE','#F6E7DE','#E3EFFA','#F2E7F0','#F7F0D9','#E0F0EC']
WHITE='#F8F8F3'; CYAN='#74E5EA'; GOLD='#F8CF8C'; MUTED='#AECBD0'; DARK='#081924'


def font_path(bold=True):
    import os
    key = 'BRAIN_FONT_BOLD' if bold else 'BRAIN_FONT_REGULAR'
    if os.environ.get(key) and Path(os.environ[key]).is_file():
        return os.environ[key]
    candidates = [
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc' if bold else '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
        '/System/Library/Fonts/PingFang.ttc',
        'C:/Windows/Fonts/msyhbd.ttc' if bold else 'C:/Windows/Fonts/msyh.ttc',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    ]
    for p in candidates:
        if Path(p).is_file(): return p
    raise FileNotFoundError('找不到支持中文的字体，请安装 Noto Sans CJK，或设置 BRAIN_FONT_BOLD 和 BRAIN_FONT_REGULAR')


class Maker:
    def __init__(self,args):
        self.args=args
        self.day=args.day
        self.kind= args.type if args.type!='auto' else ['disc','balls','memory'][(args.day-1)%3]
        self.seed= args.seed if args.seed is not None else 20261118+args.day*103
        self.rng=random.Random(self.seed)
        self.W,self.H=(540,960) if args.preview else (1080,1920)
        self.k=self.W/1080
        self.fps=5 if args.preview else args.fps
        self.out=Path(args.output_dir or f'output/DAY{args.day:02d}_{self.kind}').resolve()
        self.out.mkdir(parents=True,exist_ok=True)
        self.fonts={}
        self.intro=4 if self.kind=='memory' else 5
        self.outro=7 if self.kind=='memory' else 4
        if self.kind=='memory':
            self.observe=3 if args.preview else 20
            self.transition=1 if args.preview else 2
            self.qsec=2 if args.preview else 10
            self.challenge=self.observe+self.transition+3*self.qsec
        else:
            self.challenge=6 if args.preview else args.challenge_seconds
        self.total=self.intro+self.challenge+self.outro
        self.data={ 'day':self.day,'type':self.kind,'seed':self.seed,'resolution':[self.W,self.H],
                    'fps':self.fps,'intro_seconds':self.intro,'challenge_seconds':self.challenge,
                    'outro_seconds':self.outro,'total_seconds':self.total,'reveal_answers':False}
        self.base=self.make_bg()
        self.prepare()

    def s(self,v):return round(v*self.k)
    def f(self,sz,bold=True):
        key=(sz,bold)
        if key not in self.fonts:
            self.fonts[key]=ImageFont.truetype(font_path(bold),max(8,self.s(sz)))
        return self.fonts[key]
    def txt(self,d,x,y,text,sz=40,fill=WHITE,bold=True):
        d.text((self.s(x),self.s(y)),str(text),font=self.f(sz,bold),fill=fill,anchor='mm')
    def rr(self,d,box,r,fill,outline=None,width=2):
        d.rounded_rectangle(tuple(self.s(x) for x in box),radius=self.s(r),fill=fill,outline=outline,width=max(1,self.s(width)))
    def make_bg(self):
        w,h=self.W,self.H
        yy=np.arange(h,dtype=np.float32)[:,None]/h
        a=np.zeros((h,w,3),dtype=np.uint8)
        a[:,:,0]=np.clip(8+8*yy,0,255).astype('uint8')
        a[:,:,1]=np.clip(23+9*yy,0,255).astype('uint8')
        a[:,:,2]=np.clip(32+12*yy,0,255).astype('uint8')
        im=Image.fromarray(a,'RGB')
        d=ImageDraw.Draw(im)
        for x in range(45,1080,90): d.line((self.s(x),0,self.s(x),h),fill='#112E39',width=1)
        for y in range(50,1920,90): d.line((0,self.s(y),w,self.s(y)),fill='#112E39',width=1)
        for _ in range(60):
            x=self.rng.randint(35,1045); y=self.rng.randint(70,1830)
            d.ellipse((self.s(x),self.s(y),self.s(x+2),self.s(y+2)),fill='#2B6170')
        return im
    def layout(self,im,heading,sub):
        d=ImageDraw.Draw(im)
        self.rr(d,(65,94,1015,167),27,'#17414D','#4A9EAD')
        self.txt(d,540,131,f'每日专注力挑战   ·   DAY {self.day:02d}',36,CYAN)
        self.txt(d,540,280,heading,86,GOLD)
        self.txt(d,540,400,sub,45,WHITE)
        d.line((self.s(110),self.s(492),self.s(970),self.s(492)),fill='#386B78',width=self.s(3))
        self.txt(d,540,1830,'不暂停 · 不回看 · 评论区留下成绩',34,MUTED,False)
    def timer(self,im,remain,progress,label):
        d=ImageDraw.Draw(im)
        self.rr(d,(80,1530,1000,1750),36,'#153542','#468494')
        self.txt(d,300,1608,label,36,WHITE)
        self.txt(d,305,1673,'按顺序寻找 · 保持专注',29,MUTED,False)
        self.rr(d,(740,1550,960,1710),25,'#244D5A','#6AB7C1')
        self.txt(d,849,1617,f'{remain:02d}',85,WHITE)
        self.txt(d,850,1690,'秒剩余',25,CYAN,False)
        self.rr(d,(125,1718,650,1731),7,'#315260')
        if progress>0:self.rr(d,(125,1718,125+max(5,525*min(1,progress)),1731),7,GOLD)

    def prepare(self):
        if self.kind=='disc':self.prepare_disc()
        elif self.kind=='balls':self.prepare_balls()
        else:self.prepare_memory()

    def prepare_disc(self):
        try:
            from shapely.geometry import Point, MultiPoint
            from shapely import voronoi_polygons
        except ImportError:
            raise RuntimeError('圆盘模式需要 shapely: pip install shapely')
        count=49; radius=410
        points=[]
        for i in range(count):
            rad=radius*.91*math.sqrt((i+.5)/count)
            theta=i*2.399963229728653
            points.append([rad*math.cos(theta),rad*math.sin(theta)])
        P=np.array(points)
        circle=Point(0,0).buffer(radius,resolution=128)
        for _ in range(3):
            v=voronoi_polygons(MultiPoint([tuple(p) for p in P]),extend_to=Point(0,0).buffer(radius+180).envelope,ordered=True)
            polys=[poly.intersection(circle) for poly in v.geoms]
            P=np.array([[poly.centroid.x,poly.centroid.y] for poly in polys])
        v=voronoi_polygons(MultiPoint([tuple(p) for p in P]),extend_to=Point(0,0).buffer(radius+180).envelope,ordered=True)
        polys=[poly.intersection(circle) for poly in v.geoms]
        self.polys=[np.array(p.exterior.coords) for p in polys]
        self.centers=[(p.centroid.x,p.centroid.y) for p in polys]
        self.nums=list(range(1,50));self.rng.shuffle(self.nums)
        self.cols=[self.rng.choice(PALETTE) for _ in range(count)]
        assert len(self.nums)==49 and set(self.nums)==set(range(1,50))
        self.data['numbers']=self.nums
        self.data['number_integrity_passed']=True
    def prepare_balls(self):
        self.nums=list(range(1,50));self.rng.shuffle(self.nums)
        self.balls=[]
        for row in range(7):
            for col in range(7):
                x=165+col*125+self.rng.uniform(-9,9)
                y=655+row*119+self.rng.uniform(-9,9)
                self.balls.append((x,y,self.rng.uniform(0,6.283),self.rng.uniform(0,6.283)))
        assert set(self.nums)==set(range(1,50))
        self.data['numbers']=self.nums
        self.data['number_integrity_passed']=True
    def prepare_memory(self):
        tiles_dir=Path(self.args.memory_tiles_dir or ROOT/'assets/memory_tiles')
        manifest=json.loads((tiles_dir/'manifest.json').read_text(encoding='utf-8'))
        items=manifest['items']
        if len(items)!=12:raise ValueError('记忆模式需要恰好12件物品')
        if len({it['name'] for it in items})!=12:raise ValueError('物品名称不能重复')
        self.items=items[:];self.rng.shuffle(self.items)
        self.tiles=[]
        for item in self.items:
            p=tiles_dir/item['file']
            if not p.is_file():raise FileNotFoundError(p)
            self.tiles.append(Image.open(p).convert('RGB'))
        fruit_count=sum(it.get('category')=='fruit' for it in self.items)
        target_name='足球' if any(it['name']=='足球' for it in self.items) else self.items[1]['name']
        target_idx=next(i for i,it in enumerate(self.items) if it['name']==target_name)
        q2_idx=self.rng.choice([i for i in range(12) if i!=target_idx])
        def position(i):return f'第{i//4+1}行第{i%4+1}列'
        def choices(correct,alternatives):
            wrong=[]
            for a in alternatives:
                if a!=correct and a not in wrong:wrong.append(a)
            if len(wrong)<2:raise ValueError('无法生成两个不同的错误选项')
            opts=[correct]+self.rng.sample(wrong,2);self.rng.shuffle(opts)
            return opts,'ABC'[opts.index(correct)]
        q1opt,q1key=choices(position(target_idx),[position(i) for i in range(12) if i!=target_idx])
        q2opt,q2key=choices(self.items[q2_idx]['name'],[it['name'] for i,it in enumerate(self.items) if i!=q2_idx])
        q3opt,q3key=choices(f'{fruit_count}种',[f'{i}种' for i in range(0,7) if i!=fruit_count])
        self.questions=[
            {'question':f'{target_name}在第几行第几列？','options':q1opt,'answer':q1key,'correct':position(target_idx)},
            {'question':f'{position(q2_idx)}是什么？','options':q2opt,'answer':q2key,'correct':self.items[q2_idx]['name']},
            {'question':'画面里共有几种水果？','options':q3opt,'answer':q3key,'correct':f'{fruit_count}种'},
        ]
        self.data['items_in_row_major_order']=[it['name'] for it in self.items]
        self.data['questions']=[{k:v for k,v in q.items() if k not in ('answer','correct')} for q in self.questions]
        self.data['answer_integrity_passed']=all(q['options'].count(q['correct'])==1 for q in self.questions)
        (self.out/'创作者专用_答案.json').write_text(json.dumps({'day':self.day,'questions':self.questions},ensure_ascii=False,indent=2),encoding='utf-8')
        self.memory_board=self.make_board()
        self.memory_board.save(self.out/'记忆题目图.png')
    def make_board(self):
        board=Image.new('RGB',(self.s(940),self.s(660)),'#102A35')
        d=ImageDraw.Draw(board)
        cw,ch=self.s(215),self.s(187)
        gapx,gapy=self.s(13),self.s(15)
        x0,y0=self.s(20),self.s(38)
        for i,src in enumerate(self.tiles):
            r,c=divmod(i,4)
            x=x0+c*(cw+gapx);y=y0+r*(ch+gapy)
            crop=src.resize((cw,ch),Image.Resampling.LANCZOS)
            board.paste(crop,(x,y))
            d.rounded_rectangle((x,y,x+cw,y+ch),radius=self.s(14),outline='#D9CDB7',width=max(1,self.s(3)))
        return board

    def draw_disc(self,im,t):
        d=ImageDraw.Draw(im)
        cx,cy=540,1025;radius=410
        angle= -.05 if t<self.intro else -.05+(.70*min(1,max(0,(t-self.intro)/self.challenge)))
        ca,sa=math.cos(angle),math.sin(angle)
        def rot(p):return (self.s(cx+p[0]*ca-p[1]*sa),self.s(cy+p[0]*sa+p[1]*ca))
        d.ellipse((self.s(cx-radius-14),self.s(cy-radius-14),self.s(cx+radius+14),self.s(cy+radius+14)),fill='#091923',outline=CYAN,width=self.s(4))
        for i,poly in enumerate(self.polys):
            pts=[rot(p) for p in poly]
            d.polygon(pts,fill=self.cols[i]);d.line(pts,fill='#243A43',width=max(2,self.s(5)),joint='curve')
        for i,p in enumerate(self.centers):
            n=self.nums[i];x,y=rot(p)
            d.text((x,y),str(n),font=self.f(40),fill='#D34C43' if n==1 else '#253640',anchor='mm')
    def draw_balls(self,im,t):
        d=ImageDraw.Draw(im)
        self.rr(d,(75,575,1005,1500),50,'#102B34','#377483')
        for i,(x,y,phase1,phase2) in enumerate(self.balls):
            dx=8*math.sin(t*.42+phase1);dy=8*math.sin(t*.35+phase2)
            px=self.s(x+dx);py=self.s(y+dy);r=self.s(45)
            d.ellipse((px-r,py-r,px+r,py+r),fill='#F8F6EF',outline='#A8D9E0',width=max(1,self.s(3)))
            d.text((px,py),str(self.nums[i]),font=self.f(35),fill='#24323B',anchor='mm')
    def draw_memory(self,im,t):
        d=ImageDraw.Draw(im)
        if t<self.intro:
            self.txt(d,540,790,f'{self.observe} 秒观察',100,GOLD)
            self.txt(d,540,980,'3 道记忆题',86,WHITE)
            self.txt(d,540,1190,'记住物品、位置和数量',50,CYAN)
            self.txt(d,540,1450,'准备开始',58,WHITE)
            return
        a=t-self.intro
        if a<self.observe:
            self.txt(d,540,530,'请记住每件物品的位置',48,WHITE)
            im.paste(self.memory_board,(self.s(70),self.s(620)))
            remain=math.ceil(self.observe-a)
            self.rr(d,(295,1370,785,1470),25,'#1B4C59','#4DAAB5')
            self.txt(d,540,1420,f'观察剩余 {remain:02d} 秒',43,GOLD)
            self.txt(d,540,1615,'从上到下数行，从左到右数列',38,MUTED,False)
        elif a<self.observe+self.transition:
            self.txt(d,540,780,'观察结束！',100,GOLD)
            self.txt(d,540,980,'图片已隐藏',60,WHITE)
            self.txt(d,540,1100,'请凭记忆回答问题',50,CYAN)
        elif a<self.challenge:
            qtime=a-self.observe-self.transition
            idx=min(2,int(qtime//self.qsec));q=self.questions[idx]
            remain=math.ceil(self.qsec-(qtime-idx*self.qsec))
            self.rr(d,(335,530,745,625),25,'#1B4C59','#4DAAB5')
            self.txt(d,540,577,f'第 {idx+1} / 3 题',43,CYAN)
            self.txt(d,540,730,q['question'],49,WHITE)
            for j,opt in enumerate(q['options']):
                y=900+j*195
                self.rr(d,(95,y,985,y+142),25,'#1A3A49','#477A8A')
                self.rr(d,(130,y+29,222,y+114),19,GOLD)
                self.txt(d,176,y+72,'ABC'[j],52,'#24323B')
                self.txt(d,605,y+72,opt,49,WHITE)
            self.txt(d,540,1625,f'剩余 {remain:02d} 秒',43,GOLD)
        else:
            self.txt(d,540,720,'挑战完成！',104,GOLD)
            self.txt(d,540,920,'你答对了几道？',69,WHITE)
            self.txt(d,540,1100,'评论区留下你的选项组合',46,CYAN)
            self.txt(d,540,1350,'不公布答案 · 明天继续',41,MUTED,False)

    def frame(self,t):
        im=self.base.copy()
        heading={'disc':'动态圆盘舒尔特','balls':'动态小球舒尔特','memory':'短时记忆挑战'}[self.kind]
        sub='90秒内从 1 找到 49' if self.kind!='memory' else '记住物品位置 · 回答3道题'
        if self.kind!='memory' and self.challenge!=90:sub=f'{self.challenge}秒内从 1 找到 49'
        self.layout(im,heading,sub)
        if self.kind=='memory':self.draw_memory(im,t)
        else:
            if self.kind=='disc':self.draw_disc(im,t)
            else:self.draw_balls(im,t)
            if t<self.intro:remain=self.challenge;label='准备开始'
            elif t<self.intro+self.challenge:
                remain=math.ceil(self.intro+self.challenge-t);label='挑战进行中'
            else:remain=0;label='挑战结束'
            self.timer(im,remain,max(0,min(1,(t-self.intro)/self.challenge)),label)
            if t>=self.intro+self.challenge:
                d=ImageDraw.Draw(im)
                self.rr(d,(110,770,970,1230),40,'#102D3C',CYAN,4)
                self.txt(d,540,900,'时间到！',95,GOLD)
                self.txt(d,540,1050,'你找到了第几个？',59,WHITE)
                self.txt(d,540,1150,'评论区留下成绩',43,CYAN)
        return im

    def make_audio(self):
        sr=16000; N=int(sr*self.total)
        t=np.arange(N,dtype=np.float32)/sr
        sound=(.008*np.sin(2*np.pi*130.81*t)+.006*np.sin(2*np.pi*196*t)+.004*np.sin(2*np.pi*261.63*t)).astype('float32')
        def tone(at,freq,dur=.14,vol=.065):
            a=int(at*sr);b=min(N,a+int(dur*sr))
            if b<=a:return
            tt=np.arange(b-a,dtype=np.float32)/sr
            sound[a:b]+=vol*np.sin(2*np.pi*freq*tt)*np.sin(np.pi*tt/dur)**2
        for at in [0,self.intro,self.intro+self.challenge]:tone(at,720,.24,.11)
        if self.kind=='memory':
            for i in range(3):tone(self.intro+self.observe+self.transition+i*self.qsec,870,.17,.10)
        else:
            for at in range(self.intro+5,self.intro+self.challenge,5):tone(at,670,.06,.02)
            for at in range(self.intro+self.challenge-5,self.intro+self.challenge):tone(at,950,.09,.045)
        sound*=np.minimum(1,t/.4)*np.minimum(1,(self.total-t)/.8)
        sound=np.clip(sound,-.85,.85)
        path=self.out/'原创背景提示音.wav'
        with wave.open(str(path),'wb') as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(sr)
            f.writeframes((sound*32767).astype('<i2').tobytes())
        return path

    def write_text(self):
        heading={'disc':'动态圆盘舒尔特','balls':'动态小球舒尔特','memory':'短时记忆挑战'}[self.kind]
        if self.kind=='memory':
            script=f'''# Day {self.day:02d} · {heading}\n\n## 分镜\n- 0–{self.intro}秒：开场，说明观察物品后答题\n- {self.intro}–{self.intro+self.observe}秒：观察12件物品\n- {self.intro+self.observe}–{self.intro+self.observe+self.transition}秒：隐藏画面\n- 接下来3题，每题{self.qsec}秒，不显示答案\n- 最后{self.outro}秒：留言互动\n\n## 口播\n- 开场：每日专注力挑战，第{self.day}天！今天是短时记忆挑战。\n- 观察前：记住物品和位置，图片消失后回答三道题。\n- 答题期间：保持安静，让观众思考。\n- 结尾：你答对了几道？把三个选项留在评论区。\n\n## 发布文案\n短时记忆挑战 Day {self.day:02d}！观察{self.observe}秒，回答3道题，不暂停、不回看。你能答对几题？评论区留下答案！\n#短时记忆 #观察力挑战 #每日专注力挑战\n\n创作者专用答案在“创作者专用_答案.json”中，不要上传该文件。\n'''
        else:
            script=f'''# Day {self.day:02d} · {heading}\n\n## 分镜\n- 0–{self.intro}秒：开场说明\n- {self.intro}–{self.intro+self.challenge}秒：从1找到49，{self.challenge}秒倒计时\n- {self.intro+self.challenge}–{self.total}秒：只显示“你找到了第几个？”\n- 不公布答案\n\n## 口播\n- 开场：每日专注力挑战，第{self.day}天！今天是{heading}。\n- 规则：{self.challenge}秒内按顺序找到一到四十九。准备，开始！\n- 挑战期间：保持安静，让观众寻找。\n- 结尾：时间到！你找到了第几个？评论区留下成绩。\n\n## 发布文案\n{self.challenge}秒挑战1–49！Day {self.day:02d}，{heading}。数字全部打乱，不暂停、不回看。你找到第几个？\n#舒尔特 #找数字 #每日专注力挑战\n'''
        (self.out/'视频脚本_发布文案.md').write_text(script,encoding='utf-8')
        def stamp(s):
            ms=int(round(s*1000));h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);sec,ms=divmod(ms,1000)
            return f'{h:02d}:{m:02d}:{sec:02d},{ms:03d}'
        if self.kind=='memory':
            cues=[(0,self.intro,'每日专注力挑战：短时记忆挑战'),(self.intro,self.intro+2,'记住物品和位置'),(self.total-self.outro,self.total,'你答对几道？评论区留言')]
        else:
            cues=[(0,self.intro,f'{self.challenge}秒找完1到49，准备开始！'),(self.total-self.outro,self.total,'时间到！你找到了第几个？')]
        srt='\n\n'.join(f'{i+1}\n{stamp(a)} --> {stamp(b)}\n{txt}' for i,(a,b,txt) in enumerate(cues))+'\n'
        (self.out/'字幕_配音参考.srt').write_text(srt,encoding='utf-8')
        (self.out/'生成参数_质检.json').write_text(json.dumps(self.data,ensure_ascii=False,indent=2),encoding='utf-8')

    def render(self):
        self.frame(self.intro+.2).save(self.out/'封面_题目.png')
        self.write_text()
        if self.args.no_video:return None
        audio=self.make_audio()
        if not shutil.which('ffmpeg'):raise RuntimeError('没有找到 ffmpeg。请先安装 FFmpeg 并确保 ffmpeg 在 PATH 中')
        video=self.out/f'DAY{self.day:02d}_{self.kind}_无答案版.mp4'
        cmd=['ffmpeg','-y','-hide_banner','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24',
             '-s',f'{self.W}x{self.H}','-r',str(self.fps),'-i','pipe:0','-i',str(audio),
             '-c:v','libx264','-preset','veryfast','-crf','23','-pix_fmt','yuv420p',
             '-c:a','aac','-b:a','96k','-t',str(self.total),'-movflags','+faststart',str(video)]
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            for i in range(int(self.total*self.fps)):
                frame=self.frame((i+.1)/self.fps)
                proc.stdin.write(frame.tobytes())
                if i and i%(self.fps*10)==0:print(f'已渲染 {i//self.fps}/{self.total} 秒',flush=True)
            proc.stdin.close();err=proc.stderr.read().decode('utf-8',errors='replace');rc=proc.wait()
            if rc:raise RuntimeError(f'FFmpeg 错误: {err[-2000:]}')
        finally:
            if proc.poll() is None:proc.kill()
        self.verify(video)
        return video
    def verify(self,video):
        if shutil.which('ffprobe'):
            p=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration',
                              '-of','default=noprint_wrappers=1:nokey=1',str(video)],capture_output=True,text=True)
            if p.returncode==0:
                length=float(p.stdout.strip())
                if abs(length-self.total)>1:raise RuntimeError(f'时长校验失败: {length} vs {self.total}')
                self.data['actual_video_duration']=round(length,3)
        self.data['video_verified']=True
        (self.out/'生成参数_质检.json').write_text(json.dumps(self.data,ensure_ascii=False,indent=2),encoding='utf-8')
    def zip_episode(self):
        zpath=self.out/f'DAY{self.day:02d}_创作者素材包.zip'
        with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED,compresslevel=5) as z:
            for p in self.out.iterdir():
                if p.is_file() and p!=zpath:z.write(p,p.name)
        return zpath


def main():
    p=argparse.ArgumentParser(description='每日专注力挑战 · 三类轮换短视频生成器')
    p.add_argument('--day',type=int,default=1,help='期数，从1开始；自动轮换圆盘、小球、记忆')
    p.add_argument('--type',choices=['auto','disc','balls','memory'],default='auto')
    p.add_argument('--seed',type=int,help='随机种子；不填则根据期数自动生成')
    p.add_argument('--challenge-seconds',type=int,default=90,help='数字搜索挑战时间，默认90秒')
    p.add_argument('--fps',type=int,default=12,help='完整版帧率，默认12fps')
    p.add_argument('--memory-tiles-dir',help='自定义记忆物品目录（12张图片+manifest.json）')
    p.add_argument('--output-dir',help='输出目录')
    p.add_argument('--preview',action='store_true',help='快速预览：540x960，缩短挑战时长')
    p.add_argument('--no-video',action='store_true',help='只生成封面、题目数据和脚本')
    p.add_argument('--no-zip',action='store_true',help='不打包本期素材')
    args=p.parse_args()
    if args.day<1 or args.challenge_seconds<1 or args.fps<1: p.error('day、challenge-seconds、fps必须大于0')
    m=Maker(args);video=m.render();z=None if args.no_zip else m.zip_episode()
    print('题型:',m.kind,'期数:',m.day,'时长:',m.total,'秒')
    if video:print('成片:',video)
    print('封面:',m.out/'封面_题目.png')
    if z:print('素材包:',z)
    print('完成。答案不显示在视频中。')

if __name__=='__main__':main()
