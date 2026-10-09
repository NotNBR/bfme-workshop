#include "symbol_groups.inc"
struct OverlayState { U32 version,candidates,groups,merged,walls,dropped,vertices,peakMerged,peakGroups;
    U32 fortress,production,economy,defense,objective,gates; };
extern "C" __declspec(dllexport) OverlayState bfxOverlay={1};
static float overlayScale=1;
static void beginOverlay() {
    memset(seenSymbols,0,sizeof(seenSymbols));sampleCount=0;
    bfxOverlay.candidates=bfxOverlay.groups=bfxOverlay.merged=bfxOverlay.walls=bfxOverlay.dropped=bfxOverlay.vertices=0;
    bfxOverlay.fortress=bfxOverlay.production=bfxOverlay.economy=bfxOverlay.defense=bfxOverlay.objective=bfxOverlay.gates=0;
}
static void countBadge(float x,float y,U32 number,float fade) {
    static const U8 masks[]={63,6,91,79,102,109,125,7,127,111};
    U32 digits[3],n=0;do{digits[n++]=number%10;number/=10;}while(number&&n<3);
    float s=overlayScale,width=(n*7+7)*s,top=y+13*s;
    U32 ink=alpha(0xF4F3D8,fade),dark=alpha(0x0D1519,fade);
    tri(x-width/2,top,x+width/2,top,x+width/2,top+14*s,dark);
    tri(x-width/2,top,x+width/2,top+14*s,x-width/2,top+14*s,dark);
    const float lines[7][4]={{0,0,4,0},{4,0,4,4},{4,4,4,8},{0,8,4,8},{0,4,0,8},{0,0,0,4},{0,4,4,4}};
    for(U32 d=0;d<n;d++)for(int seg=0;seg<7;seg++)if(masks[digits[n-1-d]]&(1<<seg)) {
        float left=x-(n*7-3)*s/2+d*7*s;
        iconLine(left+lines[seg][0]*s,top+3*s+lines[seg][1]*s,left+lines[seg][2]*s,top+3*s+lines[seg][3]*s,1.35f*s,ink);
    }
}
static void roleMarker(SymbolKind kind,float x,float y,bool selected,U32 color,float fade) {
    static const V2 box[]={{-1,-1},{1,-1},{1,1},{-1,1}};
    static const V2 diamondShape[]={{0,-1.1f},{1.1f,0},{0,1.1f},{-1.1f,0}};
    static const V2 triangle[]={{0,-1.15f},{1,.8f},{-1,.8f}};
    static const V2 keep[]={{-1,1},{1,1},{1,-1},{.4f,-1},{.4f,-.5f},{-.4f,-.5f},{-.4f,-1},{-1,-1}};
    const V2 *shape=diamondShape;int n=4;
    if(kind==ARCHER||kind==PIKE){shape=triangle;n=3;}
    if(kind==SIEGE||buildingKind(kind))shape=box;
    if(kind==FORTRESS){shape=keep;n=8;}
    if(kind==HERO||kind==AIR||kind==MONSTER||kind==BUILDER) {
        U32 first=vertexCount;
        tacticalSymbol(kind,x,y,selected,alpha(color,fade),alpha(0xF4F3D8,fade),alpha(0xF4F3D8,fade),alpha(0x0D1519,fade));
        for(U32 v=first;v<vertexCount;v++){vertices[v].x=x+(vertices[v].x-x)*overlayScale;vertices[v].y=y+(vertices[v].y-y)*overlayScale;}
        return;
    }
    float s=overlayScale;U32 paper=alpha(0xF4F3D8,fade),dark=alpha(0x0D1519,fade);
    iconPolygon(x,y,11.5f*s,shape,n,selected?alpha(0xFFE45C,fade):paper);
    iconPolygon(x,y,10.5f*s,shape,n,dark);iconPolygon(x,y,8.5f*s,shape,n,alpha(color,fade));
    iconPolygon(x,y,4.8f*s,shape,n,dark);iconPolygon(x,y,3.5f*s,shape,n,paper);
    if(kind==CAVALRY||kind==PIKE)iconLine(x,y-7*s,x,y+7*s,1.4f*s,dark);
    if(buildingKind(kind)) {
        // Simple high-contrast interior glyphs: doorway, factory, coin, tower, flag.
        square(x,y,5*s,alpha(color,fade));
        if(kind==GATE||kind==BUILDING) {
            iconLine(x-3*s,y+4*s,x-3*s,y-3*s,1.6f*s,dark);iconLine(x+3*s,y+4*s,x+3*s,y-3*s,1.6f*s,dark);
            iconLine(x-3*s,y-3*s,x+3*s,y-3*s,1.6f*s,dark);
        } else if(kind==ECONOMY) {diamond(x,y,4*s,paper);square(x,y,1.5f*s,dark);}
        else if(kind==PRODUCTION) {iconLine(x-4*s,y+3*s,x+4*s,y+3*s,2*s,dark);iconLine(x-3*s,y+3*s,x-3*s,y-4*s,2*s,dark);iconLine(x,y+3*s,x,y-1*s,2*s,dark);}
        else if(kind==OBJECTIVE) {iconLine(x-2*s,y+4*s,x-2*s,y-5*s,1.5f*s,dark);tri(x-2*s,y-5*s,x+5*s,y-3*s,x-2*s,y,dark);}
        else {iconLine(x-3*s,y-3*s,x+3*s,y-3*s,2*s,dark);iconLine(x,y-3*s,x,y+4*s,3*s,dark);}
    }
    bfxSymbolTypes.current[buildingKind(kind)?BUILDING:kind]++;
}
static V2 footprintPoints[256],footprintHull[512];
static int pointCompare(const void *a,const void *b) {
    const V2 &x=*(const V2*)a,&y=*(const V2*)b;
    return x.x<y.x?-1:x.x>y.x?1:x.y<y.y?-1:x.y>y.y?1:0;
}
static float turn(const V2 &o,const V2 &a,const V2 &b){return (a.x-o.x)*(b.y-o.y)-(a.y-o.y)*(b.x-o.x);}
static void groupFootprint(const SymbolGroup &g,float fade,U32 reserve) {
    if(g.count<2)return;
    int n=0;float padding=9*overlayScale;
    for(U32 i=0;i<g.count;i++) {
        const SymbolSample &s=symbolSamples[g.members[i]];
        for(int j=0;j<4;j++){V2 &p=footprintPoints[n++];p.x=s.x+(j==0?padding:j==2?-padding:0);p.y=s.y+(j==1?padding:j==3?-padding:0);}
    }
    qsort(footprintPoints,n,sizeof(V2),pointCompare);int k=0;
    for(int i=0;i<n;i++){while(k>=2&&turn(footprintHull[k-2],footprintHull[k-1],footprintPoints[i])<=0)k--;footprintHull[k++]=footprintPoints[i];}
    int lower=k+1;
    for(int i=n-2;i>=0;i--){while(k>=lower&&turn(footprintHull[k-2],footprintHull[k-1],footprintPoints[i])<=0)k--;footprintHull[k++]=footprintPoints[i];}k--;
    if(vertexCount+k*9+reserve>SYMBOL_VERTEX_CAPACITY)return;
    // 13% tint with a transparent outer fringe; no circular range indicator.
    U32 tint=alpha(g.seed.color,fade*.13f),clear=alpha(g.seed.color,0);
    for(int i=0;i<k;i++) {
        V2 a=footprintHull[i],b=footprintHull[(i+1)%k];tri(g.x,g.y,a.x,a.y,b.x,b.y,tint);
        float ax=a.x-g.x,ay=a.y-g.y,bx=b.x-g.x,by=b.y-g.y;
        float al=(float)sqrt(ax*ax+ay*ay),bl=(float)sqrt(bx*bx+by*by);
        V2 ao={a.x+ax*5/(al+1),a.y+ay*5/(al+1)},bo={b.x+bx*5/(bl+1),b.y+by*5/(bl+1)};
        U32 start=vertexCount;tri(a.x,a.y,ao.x,ao.y,bo.x,bo.y,tint);tri(a.x,a.y,bo.x,bo.y,b.x,b.y,tint);
        vertices[start+1].color=vertices[start+2].color=vertices[start+4].color=clear;
    }
}
static void drawOverlay(float fade,float height,const Viewport &vp) {
    overlayScale=(float)vp.height/1080;if(overlayScale<.85f)overlayScale=.85f;if(overlayScale>1.5f)overlayScale=1.5f;
    groupSymbols(height>2400?30*overlayScale:0);
    bfxOverlay.candidates=sampleCount;bfxOverlay.groups=clusterCount;bfxOverlay.merged=sampleCount-clusterCount;
    if(bfxOverlay.merged>bfxOverlay.peakMerged)bfxOverlay.peakMerged=bfxOverlay.merged;
    if(bfxOverlay.groups>bfxOverlay.peakGroups)bfxOverlay.peakGroups=bfxOverlay.groups;
    int admitted=clusterCount;if(admitted>(int)(SYMBOL_VERTEX_CAPACITY/384))admitted=SYMBOL_VERTEX_CAPACITY/384;
    bfxOverlay.dropped+=clusterCount-admitted;
    placeMarkers(admitted,overlayScale,vp);
    // Admit highest priorities first; draw them last. Reserve whole marker budgets.
    for(int g=0;g<admitted;g++)groupFootprint(symbolClusters[g],fade,admitted*384);
    for(int g=admitted-1;g>=0;g--) {
        SymbolGroup &c=symbolClusters[g];SymbolSample &s=c.seed;
        if(s.kind==WALL) {
            iconLine(s.x-s.wallX,s.y-s.wallY,s.x+s.wallX,s.y+s.wallY,2*overlayScale,alpha(s.selected?0xFFE45C:s.color,fade*.8f));
            bfxOverlay.walls++;bfxState.buildings++;continue;
        }
        if(fabs(c.drawX-c.x)+fabs(c.drawY-c.y)>1)
            iconLine(c.x,c.y,c.drawX,c.drawY,overlayScale,alpha(s.color,fade*.45f));
        roleMarker(s.kind,c.drawX,c.drawY,s.selected,s.color,fade);
        if(c.count>1)countBadge(c.drawX,c.drawY,c.count,fade);
        if(s.selected)bfxSymbols.selectedIcons++;
        if(s.enemy)bfxSymbols.enemyIcons++;
        if(buildingKind(s.kind))bfxState.buildings++;else bfxState.units++;
        if(s.kind==FORTRESS)bfxOverlay.fortress++;if(s.kind==PRODUCTION)bfxOverlay.production++;
        if(s.kind==ECONOMY)bfxOverlay.economy++;if(s.kind==DEFENSE)bfxOverlay.defense++;
        if(s.kind==OBJECTIVE)bfxOverlay.objective++;if(s.kind==GATE)bfxOverlay.gates++;
        bfxState.icons++;
    }
    bfxOverlay.vertices=vertexCount;
}
