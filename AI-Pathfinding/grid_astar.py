#!/usr/bin/env python3
"""
Grid A* pathfinder (0,0 = bottom-left corner)

Reads:
  GET http://localhost:8765/waypoints        -> {"data":[{"r":..,"c":..,"label":"START|WAYPOINT|END"}, ...]}
  GET http://localhost:8765/grid/obstacles   -> list OR {"data":[{r,c}|{x,y}, ...]}

Writes:
  PUT http://localhost:8765/grid/path        -> bare JSON list [{"r":int,"c":int}, ...]

Conventions:
  • Hard-coded grid: 0 ≤ r < 31, 0 ≤ c < 48
  • (0,0) = bottom-left corner
  • r increases upward, c increases rightward
  • 8-direction movement, feet-based costs
"""

from __future__ import annotations
import asyncio, json, math, hashlib, time
from typing import Dict, Iterable, List, Optional, Tuple
import aiohttp

# ----------------- Endpoints -----------------
WAYPOINTS_URL = "http://localhost:8765/waypoints"
OBSTACLES_URL = "http://localhost:8765/grid/obstacles"
PATH_PUT_URL  = "http://localhost:8765/grid/path"

# ----------------- Grid bounds -----------------
MAX_ROW = 31   # rows: 0..30 (bottom to top)
MAX_COL = 48   # cols: 0..47 (left to right)

# ----------------- Movement scales (feet) -----------------
X_SCALE, Y_SCALE, DIAG_SCALE = 7.5, 5.16129, 9.104334
MAX_CABLE_FT = 300.0

# ----------------- Watcher -----------------
POLL_INTERVAL_SEC, DEBOUNCE_MS, COOLDOWN_SEC = 2.0, 150, 2.0

# ----------------- Helpers -----------------
def _unwrap_data(obj):
    return obj["data"] if isinstance(obj, dict) and "data" in obj else obj

def _pt_from_rc_or_xy(p)->Tuple[int,int]:
    if not isinstance(p,dict):raise ValueError(f"Point not dict:{p}")
    if "r" in p and "c" in p: return int(p["r"]),int(p["c"])
    if "x" in p and "y" in p: return int(p["y"]),int(p["x"])
    raise ValueError(f"Missing r/c or x/y:{p}")

def _hash_text(s:str)->str: return hashlib.sha256(s.encode()).hexdigest()

# ----------------- Coordinate transform -----------------
def to_internal(r:int)->int:
    """Convert user row (0=bottom) → internal row (0=top)."""
    return (MAX_ROW - 1) - r

def from_internal(r:int)->int:
    """Convert internal row back to user row."""
    return (MAX_ROW - 1) - r

# ----------------- Distance -----------------
def segment_length_feet(a:Tuple[int,int],b:Tuple[int,int])->float:
    ar,ac=a;br,bc=b;dr,dc=abs(br-ar),abs(bc-ac)
    if dr==0 and dc==0:return 0.0
    d=min(dr,dc)
    return d*DIAG_SCALE+(dr-d)*Y_SCALE+(dc-d)*X_SCALE

def polyline_feet(path:List[Tuple[int,int]])->float:
    return sum(segment_length_feet(path[i],path[i+1]) for i in range(len(path)-1))

# ----------------- Heuristic -----------------
def h_feet(a,b)->float:
    dx,dy=abs(a[1]-b[1]),abs(a[0]-b[0])
    d=min(dx,dy);rem=max(dx,dy)-d
    diag=min(DIAG_SCALE,X_SCALE+Y_SCALE)
    straight=min(X_SCALE,Y_SCALE)
    return d*diag+rem*straight

# ----------------- A* -----------------
def neighbors_8(r:int,c:int):
    for dr,dc in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
        yield r+dr,c+dc

def astar_feet(start:Tuple[int,int],goal:Tuple[int,int],obstacles:set[Tuple[int,int]])->Optional[Tuple[List[Tuple[int,int]],float]]:
    """A* search within 31x48 grid (internal top-down orientation)."""
    import heapq
    def inb(r,c): return 0<=r<MAX_ROW and 0<=c<MAX_COL
    openh=[(0.0,start)]
    g={start:0.0};came={}
    while openh:
        _,cur=heapq.heappop(openh)
        if cur==goal:
            path=[cur]
            while cur in came:
                cur=came[cur];path.append(cur)
            path.reverse()
            return path,g[goal]
        cr,cc=cur
        for nr,nc in neighbors_8(cr,cc):
            if not inb(nr,nc):continue
            if (nr,nc) in obstacles:continue
            cost=segment_length_feet((cr,cc),(nr,nc))
            newg=g[cur]+cost
            if newg<g.get((nr,nc),1e9):
                g[(nr,nc)]=newg;came[(nr,nc)]=cur
                heapq.heappush(openh,(newg+h_feet((nr,nc),goal),(nr,nc)))
    return None

# ----------------- Waypoints -----------------
def classify_waypoints(items:List[dict])->Tuple[Tuple[int,int],List[Tuple[int,int]],Tuple[int,int]]:
    s=e=None;m=[]
    for p in items:
        r,c=_pt_from_rc_or_xy(p);label=str(p.get("label","")).strip().upper()
        if label=="START":s=(r,c)
        elif label=="END":e=(r,c)
        else:m.append((r,c))
    if s is None or e is None:raise ValueError("Missing START or END")
    return s,m,e

# ----------------- Path composition -----------------
def compute_path_through_waypoints(start,mids,end,obstacles)->Tuple[List[Tuple[int,int]],float]:
    """Concatenate A* legs. User coords (0,0 bottom-left)."""
    # Map everything to internal coords
    to_int=lambda pt:(to_internal(pt[0]),pt[1])
    start_i,to_i,end_i=to_int(start),[to_int(p) for p in mids],to_int(end)
    obs_i={(to_internal(r),c) for (r,c) in obstacles}

    full_i=[];total=0.0;cur=start_i
    for nxt in to_i+[end_i]:
        res=astar_feet(cur,nxt,obs_i)
        if res is None: raise RuntimeError(f"No path {cur}->{nxt}")
        seg,cost=res;total+=cost
        full_i.extend(seg[1:] if full_i else seg)
        cur=nxt

    # Convert back to user coords (bottom-left)
    full_user=[(from_internal(r),c) for r,c in full_i]

    check=polyline_feet(full_i)
    if abs(check-total)>1e-6:print(f"[warn] A*={total:.4f}, poly={check:.4f}")
    return full_user,total

# ----------------- IO -----------------
async def fetch_json(session,url):
    async with session.get(url) as r:
        r.raise_for_status()
        try:return await r.json()
        except: return json.loads(await r.text())

async def put_path(session,path):
    pts=[{"r":int(r),"c":int(c)} for r,c in path]
    async with session.put(PATH_PUT_URL,json=pts) as r:
        txt=await r.text();ok=200<=r.status<300
        stamp=time.strftime("%Y-%m-%d %H:%M:%S")
        if ok:print(f"[{stamp}] [ok] PUT /grid/path ({len(pts)} pts)")
        else:print(f"[{stamp}] [err] PUT /grid/path {r.status}: {txt[:120]}")

# ----------------- Watch loop -----------------
async def load_inputs(session):
    w=_unwrap_data(await fetch_json(session,WAYPOINTS_URL))
    o=_unwrap_data(await fetch_json(session,OBSTACLES_URL))
    s,m,e=classify_waypoints(w)
    obs=set(_pt_from_rc_or_xy(p) for p in o)
    return s,m,e,obs,_hash_text(json.dumps(w,sort_keys=True)),_hash_text(json.dumps(o,sort_keys=True))

async def recompute_once(session):
    s,m,e,o,_,_=await load_inputs(session)
    path,total=compute_path_through_waypoints(s,m,e,o)
    print(f"[info] path length (A*): {total:.3f} ft")
    if total>MAX_CABLE_FT:print("NO VIABLE PATH");return
    await put_path(session,path)

class WatchState:
    def __init__(self):self.hw=self.ho=None;self.cool_until=0.0

async def watch_loop():
    st=WatchState()
    print(f"[watch] interval={POLL_INTERVAL_SEC}s debounce={DEBOUNCE_MS}ms")
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
        try:await recompute_once(s);_,_,_,_,st.hw,st.ho=await load_inputs(s)
        except Exception as e:print(f"[error] init:{e}")
        while True:
            await asyncio.sleep(POLL_INTERVAL_SEC)
            try:
                await asyncio.sleep(DEBOUNCE_MS/1000)
                s_,m_,e_,o_,hw,ho=await load_inputs(s)
                if hw==st.hw and ho==st.ho:continue
                print("[watch] change detected")
                if time.time()<st.cool_until:continue
                try:
                    p,t=compute_path_through_waypoints(s_,m_,e_,o_)
                    print(f"[info] path length (A*): {t:.3f} ft")
                    if t<=MAX_CABLE_FT:
                        await put_path(s,p);st.hw,st.ho=hw,ho;st.cool_until=time.time()+COOLDOWN_SEC
                    else:print("NO VIABLE PATH")
                except Exception as e:print(f"[error] recompute:{e}")
            except Exception as e:print(f"[error] loop:{e}")

def main():
    try:asyncio.run(watch_loop())
    except KeyboardInterrupt:print("\n[shutdown] bye!")

if __name__=="__main__":main()
