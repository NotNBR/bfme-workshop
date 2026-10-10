// Union of local soldier footprints. Connectivity never fills the space between them.
static const int AREA_MAX_SAMPLES=16384, AREA_HASH_SIZE=32768;
struct AreaSample {
    U32 id,owner,color;
    SymbolKind kind;
    bool selected,enemy;
    float x,y,wx,wy,padding,drawX,drawY,drawPadding;
    int parent,next,memberNext;
};
struct AreaGroup { int first;U32 count; };
static AreaSample areaSamples[AREA_MAX_SAMPLES];
static AreaGroup areaGroups[AREA_MAX_SAMPLES];
static int areaCount,areaGroupCount,areaGrid[AREA_HASH_SIZE];
// Preserve the counted-overlay diagnostics ABI; append area-specific counters.
struct OverlayState { U32 version,candidates,groups,merged,walls,dropped,vertices,peakMerged,peakGroups;
    U32 fortress,production,economy,defense,objective,gates,areas,heroes,soldiers; };
extern "C" __declspec(dllexport) OverlayState bfxOverlay={2};
static bool areaUnit(SymbolKind kind) { return kind!=HERO&&!buildingKind(kind); }
static int areaCell(int x,int y) { return (int)(((U32)x*73856093u^(U32)y*19349663u)&(AREA_HASH_SIZE-1)); }
static int areaRoot(int i) {
    int root=i;while(areaSamples[root].parent!=root)root=areaSamples[root].parent;
    while(i!=root){int next=areaSamples[i].parent;areaSamples[i].parent=root;i=next;}
    return root;
}
static void beginOverlay() {
    areaCount=areaGroupCount=0;
    bfxOverlay.candidates=bfxOverlay.groups=bfxOverlay.merged=bfxOverlay.walls=bfxOverlay.dropped=bfxOverlay.vertices=0;
    bfxOverlay.fortress=bfxOverlay.production=bfxOverlay.economy=bfxOverlay.defense=bfxOverlay.objective=bfxOverlay.gates=0;
    bfxOverlay.areas=bfxOverlay.heroes=bfxOverlay.soldiers=0;
}
static void groupUnitAreas() {
    areaGroupCount=0;
    memset(areaGrid,0xff,sizeof(areaGrid));
    for(int i=0;i<areaCount;i++) {
        AreaSample &s=areaSamples[i];s.parent=i;s.memberNext=-1;
        if(!areaUnit(s.kind))continue;
        // Projected radii are at most 12 pixels. Include only the soft outer fringe
        // in the broad phase, so disconnected fills can never overdraw each other.
        int cx=(int)floor(s.drawX/32),cy=(int)floor(s.drawY/32);
        for(int y=cy-1;y<=cy+1;y++)for(int x=cx-1;x<=cx+1;x++) {
            for(int j=areaGrid[areaCell(x,y)];j>=0;j=areaSamples[j].next) {
                AreaSample &other=areaSamples[j];
                if(s.owner!=other.owner||s.selected!=other.selected)continue;
                float dx=s.drawX-other.drawX,dy=s.drawY-other.drawY;
                float limit=s.drawPadding+other.drawPadding+1.5f;
                if(dx*dx+dy*dy>limit*limit)continue;
                int a=areaRoot(i),b=areaRoot(j);
                if(areaSamples[a].id<areaSamples[b].id)areaSamples[b].parent=a;
                else areaSamples[a].parent=b;
            }
        }
        int cell=areaCell(cx,cy);s.next=areaGrid[cell];areaGrid[cell]=i;
    }
    for(int i=0;i<areaCount;i++){areaGroups[i].first=-1;areaGroups[i].count=0;}
    for(int i=0;i<areaCount;i++) {
        int root=areaRoot(i);AreaSample &s=areaSamples[i];AreaGroup &g=areaGroups[root];
        s.memberNext=g.first;g.first=i;g.count++;
    }
    for(int i=0;i<areaCount;i++)if(areaGroups[i].count)areaGroupCount++;
}
// Ease each actual footprint rather than a group's convex outline. A merge or
// split has no cached hull to jump between, and a hidden member vanishes at once.
struct AreaHistory { U32 key,owner,frame;float x,y,radius,vx,vy,vr,opacity; };
static AreaHistory areaHistory[AREA_HASH_SIZE];
static U32 areaFrame,areaViewportWidth,areaViewportHeight;
static void resetAreaBlending(){memset(areaHistory,0,sizeof(areaHistory));areaFrame=0;}
static void dampAreaPoint(float target,float dt,float &value,float &velocity) {
    const float rate=28;
    float delta=value-target,term=(velocity+rate*delta)*dt,decay=(float)exp(-rate*dt);
    value=target+(delta+term)*decay;velocity=(velocity-rate*term)*decay;
}
static int areaHistorySlot(U32 id) {
    int firstStale=-1;
    U32 slot=(id*2654435761u)&(AREA_HASH_SIZE-1);
    for(int probe=0;probe<AREA_HASH_SIZE;probe++,slot=(slot+1)&(AREA_HASH_SIZE-1)) {
        AreaHistory &h=areaHistory[slot];
        if(h.key==id)return slot;
        if(!h.key)return firstStale>=0?firstStale:(int)slot;
        if(firstStale<0&&h.frame+1<areaFrame)firstStale=slot;
    }
    return firstStale;
}
static void prepareAreaBlending(const Viewport &vp,float dt) {
    if(areaViewportWidth!=vp.width||areaViewportHeight!=vp.height)resetAreaBlending();
    areaViewportWidth=vp.width;areaViewportHeight=vp.height;areaFrame++;
    for(int i=0;i<areaCount;i++) {
        AreaSample &s=areaSamples[i];s.drawX=s.x;s.drawY=s.y;s.drawPadding=s.padding;
        if(!areaUnit(s.kind))continue;
        int slot=areaHistorySlot(s.id);if(slot<0)continue;
        AreaHistory &h=areaHistory[slot];
        bool fresh=h.key!=s.id||h.owner!=s.owner||h.frame+1!=areaFrame;
        float dx=h.x-s.x,dy=h.y-s.y;
        if(fresh||dt<=0||dx*dx+dy*dy>480*480) {
            h.x=s.x;h.y=s.y;h.radius=s.padding;h.vx=h.vy=h.vr=0;
        } else {
            dampAreaPoint(s.x,dt,h.x,h.vx);dampAreaPoint(s.y,dt,h.y,h.vy);
            dampAreaPoint(s.padding,dt,h.radius,h.vr);
        }
        if(fresh)h.opacity=dt>0?0:1;
        h.opacity=dt>0?1-(1-h.opacity)*(float)exp(-24*dt):1;
        h.key=s.id;h.owner=s.owner;h.frame=areaFrame;
        s.drawX=h.x;s.drawY=h.y;s.drawPadding=h.radius*h.opacity;
    }
}
struct AreaFadePoint {float x,y,opacity;};
static int clipAreaFade(AreaFadePoint *in,int count,AreaFadePoint *out,int axis,float edge,bool greater) {
    int n=0;if(!count)return 0;
    AreaFadePoint a=in[count-1];float av=(axis?a.y:a.x)-edge;bool ai=greater?av>=0:av<=0;
    for(int i=0;i<count;i++) {
        AreaFadePoint b=in[i];float bv=(axis?b.y:b.x)-edge;bool bi=greater?bv>=0:bv<=0;
        if(ai!=bi){float t=av/(av-bv);AreaFadePoint &p=out[n++];p.x=a.x+t*(b.x-a.x);p.y=a.y+t*(b.y-a.y);p.opacity=a.opacity+t*(b.opacity-a.opacity);}
        if(bi)out[n++]=b;a=b;av=bv;ai=bi;
    }
    return n;
}
static bool drawAreaTriangle(V2 a,V2 b,V2 c,float aa,float ba,float ca,U32 fill,const Viewport &vp,U32 reserve) {
    float hudTop=vp.y+vp.height*(1-260.0f/768)-2,hudRight=vp.x+vp.width*(400.0f/1024)+2;
    for(int part=0;part<2;part++) {
        AreaFadePoint in[12]={{a.x,a.y,aa},{b.x,b.y,ba},{c.x,c.y,ca}},out[12];
        int n=clipAreaFade(in,3,out,0,part?hudRight:vp.x+2,true);
        n=clipAreaFade(out,n,in,0,vp.x+vp.width-2,false);
        n=clipAreaFade(in,n,out,1,part?hudTop:vp.y+2,true);
        n=clipAreaFade(out,n,in,1,part?vp.y+vp.height-2:hudTop,false);
        if(n<3)continue;
        if(vertexCount+(n-2)*3+reserve>SYMBOL_VERTEX_CAPACITY)return false;
        for(int i=1;i<n-1;i++) {
            U32 start=vertexCount;tri(in[0].x,in[0].y,in[i].x,in[i].y,in[i+1].x,in[i+1].y,fill);
            vertices[start].color=alpha(fill,in[0].opacity);
            vertices[start+1].color=alpha(fill,in[i].opacity);
            vertices[start+2].color=alpha(fill,in[i+1].opacity);
        }
    }
    return true;
}
// A sampled signed-distance union preserves concavities, holes and empty gaps.
// Only the union's outer edge receives a border; overlap never adds opacity.
static const int AREA_FIELD_WIDTH=2048,AREA_FIELD_HEIGHT=1536;
static float areaField[AREA_FIELD_WIDTH*AREA_FIELD_HEIGHT];
struct AreaFieldPoint {float x,y,d;};
static int clipAreaField(AreaFieldPoint *in,int count,AreaFieldPoint *out,float edge,bool greater) {
    int n=0;if(!count)return 0;
    AreaFieldPoint a=in[count-1];float av=a.d-edge;bool ai=greater?av>=0:av<=0;
    for(int i=0;i<count;i++) {
        AreaFieldPoint b=in[i];float bv=b.d-edge;bool bi=greater?bv>=0:bv<=0;
        if(ai!=bi){float t=av/(av-bv);AreaFieldPoint &p=out[n++];p.x=a.x+t*(b.x-a.x);p.y=a.y+t*(b.y-a.y);p.d=edge;}
        if(bi)out[n++]=b;a=b;av=bv;ai=bi;
    }
    return n;
}
static float areaEdgeAlpha(float distance,float fill) {
    if(distance<=-1.5f)return fill;
    if(distance<=-.5f)return fill+(.70f-fill)*(distance+1.5f);
    if(distance>=.75f)return 0;
    return .70f*(.75f-distance)/1.25f;
}
static bool drawAreaFieldTriangle(AreaFieldPoint a,AreaFieldPoint b,AreaFieldPoint c,U32 color,float fill,float fade,const Viewport &vp,U32 reserve) {
    // Clip at the alpha slope changes, then clip the resulting colored geometry
    // around the HUD. This keeps both the border and HUD seam smooth.
    static const float edges[]={-1000,-1.5f,-.5f,.75f};
    for(int band=0;band<3;band++) {
        AreaFieldPoint in[8]={a,b,c},out[8];
        int n=clipAreaField(in,3,out,edges[band],true);
        n=clipAreaField(out,n,in,edges[band+1],false);
        for(int i=1;i<n-1;i++) {
            V2 x={in[0].x,in[0].y},y={in[i].x,in[i].y},z={in[i+1].x,in[i+1].y};
            if(!drawAreaTriangle(x,y,z,areaEdgeAlpha(in[0].d,fill)*fade,
                areaEdgeAlpha(in[i].d,fill)*fade,areaEdgeAlpha(in[i+1].d,fill)*fade,color,vp,reserve))return false;
        }
    }
    return true;
}
static void redistanceAreaInterior(int width,int height,float step) {
    // min(circle distances) locates the union's zero contour correctly, but its
    // interior distances retain individual circle seams. Re-distance from the
    // actual exterior so touching circles lose their internal border completely.
    static const int ox[]={-1,0,1,-1,1,-1,0,1},oy[]={-1,-1,-1,0,0,1,1,1};
    for(int y=0;y<height;y++)for(int x=0;x<width;x++) {
        float &value=areaField[y*width+x];if(value>0)continue;
        float distance=1000,original=value;
        for(int i=0;i<8;i++) {
            int nx=x+ox[i],ny=y+oy[i];if(nx<0||nx>=width||ny<0||ny>=height)continue;
            float neighbor=areaField[ny*width+nx];if(neighbor<=0)continue;
            float edge=-original/(neighbor-original)*step*(ox[i]&&oy[i]?1.41421356f:1);
            if(edge<distance)distance=edge;
        }
        if(distance<.0001f)distance=.0001f;value=-distance;
    }
    for(int pass=0;pass<2;pass++) {
        int dir=pass?-1:1;
        for(int y=pass?height-1:0;y>=0&&y<height;y+=dir)for(int x=pass?width-1:0;x>=0&&x<width;x+=dir) {
            float &value=areaField[y*width+x];if(value>=0)continue;
            for(int i=0;i<4;i++) {
                int nx=i==0?x-dir:i==1?x:x+(i==2?-1:1),ny=i==0?y:y-dir;
                if(nx<0||nx>=width||ny<0||ny>=height)continue;
                float neighbor=areaField[ny*width+nx];if(neighbor>=0)continue;
                float candidate=neighbor-step*(i>=2?1.41421356f:1);
                if(candidate>value)value=candidate;
            }
        }
    }
}
static bool drawAreaUnion(const AreaGroup &g,U32 color,float fill,float fade,const Viewport &vp,U32 reserve) {
    float step=1;
    if(vp.width/(float)(AREA_FIELD_WIDTH-3)>step)step=vp.width/(float)(AREA_FIELD_WIDTH-3);
    if(vp.height/(float)(AREA_FIELD_HEIGHT-3)>step)step=vp.height/(float)(AREA_FIELD_HEIGHT-3);
    float left=(float)(vp.x+vp.width),top=(float)(vp.y+vp.height),right=(float)vp.x,bottom=(float)vp.y;
    for(int i=g.first;i>=0;i=areaSamples[i].memberNext) {
        const AreaSample &s=areaSamples[i];float r=s.drawPadding+.75f+step;
        if(s.drawX-r<left)left=s.drawX-r;if(s.drawX+r>right)right=s.drawX+r;
        if(s.drawY-r<top)top=s.drawY-r;if(s.drawY+r>bottom)bottom=s.drawY+r;
    }
    // Align the field to viewport pixels, never to a changing group's bounding box.
    if(left<vp.x)left=(float)vp.x;if(top<vp.y)top=(float)vp.y;
    if(right>vp.x+vp.width)right=(float)(vp.x+vp.width);if(bottom>vp.y+vp.height)bottom=(float)(vp.y+vp.height);
    left=vp.x+(float)floor((left-vp.x)/step)*step;top=vp.y+(float)floor((top-vp.y)/step)*step;
    int width=(int)ceil((right-left)/step)+1,height=(int)ceil((bottom-top)/step)+1;
    if(width<2||height<2)return true;
    if(width>AREA_FIELD_WIDTH||height>AREA_FIELD_HEIGHT)return false;
    for(int j=0;j<width*height;j++)areaField[j]=.75f+step*2;
    for(int i=g.first;i>=0;i=areaSamples[i].memberNext) {
        const AreaSample &s=areaSamples[i];float radius=s.drawPadding+.75f+step*2;
        int x0=(int)floor((s.drawX-radius-left)/step),x1=(int)ceil((s.drawX+radius-left)/step);
        int y0=(int)floor((s.drawY-radius-top)/step),y1=(int)ceil((s.drawY+radius-top)/step);
        if(x0<0)x0=0;if(y0<0)y0=0;if(x1>=width)x1=width-1;if(y1>=height)y1=height-1;
        for(int y=y0;y<=y1;y++)for(int x=x0;x<=x1;x++) {
            float dx=left+x*step-s.drawX,dy=top+y*step-s.drawY;
            float d=(float)sqrt(dx*dx+dy*dy)-s.drawPadding;
            float &value=areaField[y*width+x];if(d<value)value=d;
        }
    }
    redistanceAreaInterior(width,height,step);
    U32 start=vertexCount;
    for(int y=0;y<height-1;y++)for(int x=0;x<width-1;) {
        float a=areaField[y*width+x],b=areaField[y*width+x+1];
        float c=areaField[(y+1)*width+x+1],d=areaField[(y+1)*width+x];
        if(a>=.75f&&b>=.75f&&c>=.75f&&d>=.75f){x++;continue;}
        float px=left+x*step,py=top+y*step;
        bool ok=true;
        if(a<=-1.5f&&b<=-1.5f&&c<=-1.5f&&d<=-1.5f) {
            // Collapse solid interior runs, keeping geometry proportional to edges.
            int end=x+1;
            while(end<width-1&&areaField[y*width+end+1]<=-1.5f&&areaField[(y+1)*width+end+1]<=-1.5f)end++;
            V2 p={px,py},q={left+end*step,py},r={q.x,py+step},s={px,r.y};
            ok=drawAreaTriangle(p,q,r,fill*fade,fill*fade,fill*fade,color,vp,reserve)&&
               drawAreaTriangle(p,r,s,fill*fade,fill*fade,fill*fade,color,vp,reserve);
            x=end;
        } else {
            AreaFieldPoint p={px,py,a},q={px+step,py,b},r={px+step,py+step,c},s={px,py+step,d};
            ok=drawAreaFieldTriangle(p,q,r,color,fill,fade,vp,reserve)&&drawAreaFieldTriangle(p,r,s,color,fill,fade,vp,reserve);
            x++;
        }
        if(!ok){vertexCount=start;return false;}
    }
    return true;
}
static void drawOverlay(float fade,float height,const Viewport &vp,float dt=0) {
    bfxOverlay.areas=bfxOverlay.heroes=bfxOverlay.soldiers=0;
    if(dt<0)dt=0;if(dt>.05f)dt=.05f;
    prepareAreaBlending(vp,dt);groupUnitAreas();
    bfxOverlay.candidates=areaCount;bfxOverlay.groups=areaGroupCount;bfxOverlay.merged=areaCount-areaGroupCount;
    if(bfxOverlay.merged>bfxOverlay.peakMerged)bfxOverlay.peakMerged=bfxOverlay.merged;
    if(bfxOverlay.groups>bfxOverlay.peakGroups)bfxOverlay.peakGroups=bfxOverlay.groups;
    U32 markerCount=0;for(int i=0;i<areaCount;i++)if(!areaUnit(areaSamples[i].kind))markerCount++;
    U32 reserve=markerCount*256;if(reserve>SYMBOL_VERTEX_CAPACITY)reserve=SYMBOL_VERTEX_CAPACITY;
    for(int i=0;i<areaCount;i++) {
        AreaGroup &g=areaGroups[i];if(!g.count||!areaUnit(areaSamples[g.first].kind))continue;
        const AreaSample &s=areaSamples[g.first];
        if(!drawAreaUnion(g,s.color,s.selected?.32f:.24f,fade,vp,reserve)){bfxOverlay.dropped++;continue;}
        bfxOverlay.areas++;bfxOverlay.soldiers+=g.count;bfxState.units++;bfxState.icons++;
        if(s.selected)bfxSymbols.selectedIcons++;if(s.enemy)bfxSymbols.enemyIcons++;
        for(int j=g.first;j>=0;j=areaSamples[j].memberNext)bfxSymbolTypes.current[areaSamples[j].kind]++;
    }
    // Legacy house markers and hero stars stay on their real anchors, above fills.
    for(int pass=0;pass<2;pass++)for(int i=0;i<areaCount;i++) {
        const AreaSample &s=areaSamples[i];if(areaUnit(s.kind)||(pass==0)!=(s.kind==HERO))continue;
        if(vertexCount+256>SYMBOL_VERTEX_CAPACITY){bfxOverlay.dropped++;continue;}
        SymbolKind kind=s.kind==HERO?HERO:BUILDING;
        tacticalSymbol(kind,s.x,s.y,s.selected,alpha(s.color,fade),alpha(s.selected?0xffe45c:0xd0c6ad,fade),alpha(0xf3e5bc,fade),alpha(0x071018,fade));
        if(kind==HERO){bfxOverlay.heroes++;bfxState.units++;}else bfxState.buildings++;
        bfxState.icons++;if(s.selected)bfxSymbols.selectedIcons++;if(s.enemy)bfxSymbols.enemyIcons++;
    }
    bfxOverlay.vertices=vertexCount;
}
