// Pure geometry and connectivity regression, using the actual native renderer.
#include <math.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
typedef unsigned char U8;typedef unsigned int U32;
struct V2 {float x,y;};struct Vertex {float x,y,z,rhw;U32 color;};
struct Viewport {U32 x,y,width,height;float minZ,maxZ;};
template<class T> static T &field(void *p,int offset){return *(T*)((char*)p+offset);}
static const U32 SYMBOL_VERTEX_CAPACITY=524280;
static Vertex vertices[SYMBOL_VERTEX_CAPACITY];static U32 vertexCount;
struct {U32 buildings,units,icons;} bfxState;
struct {U32 selectedIcons,enemyIcons;} bfxSymbols;
static void tri(float ax,float ay,float bx,float by,float cx,float cy,U32 color) {
    if(vertexCount+3>SYMBOL_VERTEX_CAPACITY){fprintf(stderr,"triangle overflow\n");exit(1);}
    Vertex v[3]={{ax,ay,0,1,color},{bx,by,0,1,color},{cx,cy,0,1,color}};
    memcpy(vertices+vertexCount,v,sizeof(v));vertexCount+=3;
}
static void square(float x,float y,float r,U32 c){tri(x-r,y-r,x+r,y-r,x+r,y+r,c);tri(x-r,y-r,x+r,y+r,x-r,y+r,c);}
static void diamond(float x,float y,float r,U32 c){tri(x,y-r,x+r,y,x,y+r,c);tri(x,y-r,x,y+r,x-r,y,c);}
static U32 alpha(U32 c,float a){return (c&0xffffff)|((U32)(a*255)<<24);}
#include "../symbols.inc"
#include "../unit_areas.inc"
static void require(bool value,const char *message){if(!value){fprintf(stderr,"FAIL: %s\n",message);exit(1);}}
static void reset(){beginOverlay();resetAreaBlending();vertexCount=0;memset(&bfxState,0,sizeof(bfxState));memset(&bfxSymbols,0,sizeof(bfxSymbols));memset(&bfxSymbolTypes,0,sizeof(bfxSymbolTypes));}
static void sample(U32 id,U32 owner,SymbolKind kind,float x,float world,bool selected=false) {
    AreaSample &s=areaSamples[areaCount++];memset(&s,0,sizeof(s));
    s.id=id;s.owner=owner;s.kind=kind;s.x=x;s.y=100;s.wx=world;s.padding=5;s.selected=selected;s.color=0x3298d0;
}
static void dump(const char *path){FILE *f=fopen(path,"w");require(f!=0,"open preview geometry");for(U32 i=0;i<vertexCount;i+=3)fprintf(f,"%.4f %.4f %.4f %.4f %.4f %.4f %u\n",vertices[i].x,vertices[i].y,vertices[i+1].x,vertices[i+1].y,vertices[i+2].x,vertices[i+2].y,vertices[i].color);fclose(f);}
static float coverage(float x,float y) {
    float result=0;
    for(U32 i=0;i<vertexCount;i+=3) {
        const Vertex &a=vertices[i],&b=vertices[i+1],&c=vertices[i+2];
        float den=(b.y-c.y)*(a.x-c.x)+(c.x-b.x)*(a.y-c.y);
        if(fabs(den)<.00001f)continue;
        float u=((b.y-c.y)*(x-c.x)+(c.x-b.x)*(y-c.y))/den;
        float v=((c.y-a.y)*(x-c.x)+(a.x-c.x)*(y-c.y))/den,w=1-u-v;
        if(u>.00001f&&v>.00001f&&w>.00001f)result+=u*(a.color>>24)+v*(b.color>>24)+w*(c.color>>24);
    }
    return result/255;
}
static void group(const Viewport &vp){prepareAreaBlending(vp,0);groupUnitAreas();}
static AreaHistory &history(U32 id){return areaHistory[areaHistorySlot(id)];}
int main(int argc,char **argv) {
    Viewport vp={0,0,1600,1200,0,1};
    reset();sample(1,1,INFANTRY,100,0);sample(2,1,ARCHER,108,60);sample(3,2,INFANTRY,108,60);
    sample(4,1,HERO,120,60);sample(5,1,HERO,121,60);sample(6,1,BUILDING,122,60);sample(7,1,BUILDER,116,60);
    group(vp);require(areaGroupCount==5,"touching mixed roles/builders share an area; owners/heroes/buildings stay separate");
    reset();sample(1,1,INFANTRY,400,0);sample(2,1,INFANTRY,425,1);drawOverlay(1,1800,vp);
    require(bfxOverlay.areas==2&&coverage(412.3f,100.27f)==0,"world proximity cannot create a straight bridge over a screen gap");
    areaSamples[1].x=413;vertexCount=0;drawOverlay(1,1800,vp);
    require(coverage(406.3f,100.27f)==0,"separate circles leave their natural gap empty");
    areaSamples[1].x=408;vertexCount=0;drawOverlay(1,1800,vp);
    require(bfxOverlay.areas==1&&coverage(404.3f,100.27f)>0,"footprints merge when they naturally intersect");
    require(coverage(401.3f,100.27f)<.25f,"overlap has one fill and no interior border or doubled opacity");
    areaSamples[1].x=409;vertexCount=0;drawOverlay(1,1800,vp);
    require(coverage(404.3f,100.27f)<.25f,"shallow circle overlap also removes the internal border");
    // A U-shaped formation must keep its open mouth and concave interior.
    reset();U32 id=1;
    for(int row=0;row<3;row++)for(int col=0;col<3;col++)if(row==0||col!=1) {
        sample(id++,1,INFANTRY,400+col*10,(float)col*20);
        areaSamples[areaCount-1].y=100+row*10;areaSamples[areaCount-1].padding=6;
    }
    drawOverlay(1,1800,vp);require(bfxOverlay.areas==1,"one connected U-shaped formation");
    require(coverage(410.23f,117.37f)==0&&coverage(410.23f,125.37f)==0,"union preserves concavity and never convex-hull bridges the mouth");
    // A ring keeps its hole instead of filling the formation's whole envelope.
    reset();for(int i=0;i<12;i++){float angle=i*6.283185307f/12;sample(i+1,1,INFANTRY,500+20*(float)cos(angle),0);areaSamples[i].y=100+20*(float)sin(angle);areaSamples[i].padding=6;}
    drawOverlay(1,1800,vp);require(bfxOverlay.areas==1&&coverage(500.23f,100.37f)==0,"connected ring retains an empty hole");
    reset();sample(1,1,INFANTRY,100,0);sample(2,1,INFANTRY,108,0,true);group(vp);require(areaGroupCount==2,"selection states stay distinct");
    reset();sample(1,1,INFANTRY,400,0);drawOverlay(1,1800,vp);
    require(bfxOverlay.areas==1&&bfxOverlay.heroes==0&&vertexCount>0,"single normal unit still has an area");
    bool border=false;
    for(U32 i=0;i<vertexCount;i++) {
        require((vertices[i].color&0xffffff)==0x3298d0&&(vertices[i].color>>24)<=178,"border retains owner hue and stays at 70 percent opacity");
        if((vertices[i].color>>24)>100)border=true;
    }
    require(border&&coverage(400.23f,100.37f)>.23f&&coverage(400.23f,100.37f)<.25f,"subtle border surrounds a translucent interior");
    areaSamples[0].x=420;vertexCount=0;drawOverlay(1,1800,vp,1.0f/60);
    require(history(1).x>400&&history(1).x<420,"moving footprint eases without snapping");
    float first=history(1).x;areaSamples[0].x=380;vertexCount=0;drawOverlay(1,1800,vp,1.0f/60);
    require(fabs(history(1).x-first)<4,"direction reversal keeps footprint velocity continuous");
    float slow,fast;
    reset();sample(1,1,INFANTRY,400,0);drawOverlay(1,1800,vp);areaSamples[0].x=420;
    for(int frame=0;frame<6;frame++){vertexCount=0;drawOverlay(1,1800,vp,1.0f/30);}slow=history(1).x;
    reset();sample(1,1,INFANTRY,400,0);drawOverlay(1,1800,vp);areaSamples[0].x=420;
    for(int frame=0;frame<12;frame++){vertexCount=0;drawOverlay(1,1800,vp,1.0f/60);}fast=history(1).x;
    require(fabs(slow-fast)<.01f,"footprint easing is independent of frame rate");
    reset();sample(1,1,INFANTRY,400,0);sample(2,1,INFANTRY,408,0);drawOverlay(1,1800,vp);
    areaSamples[1].x=450;vertexCount=0;drawOverlay(1,1800,vp,1.0f/60);
    require(history(1).x==400&&history(2).x<450,"splitting does not replace or stretch a cached formation outline");
    areaCount=1;vertexCount=0;drawOverlay(1,1800,vp,1.0f/60);
    require(coverage(407.23f,100.37f)==0,"removed/hidden soldier extent disappears immediately");
    reset();sample(1,1,HERO,400,0);drawOverlay(1,4800,vp);require(bfxOverlay.areas==0&&bfxOverlay.heroes==1&&bfxSymbolTypes.current[HERO]==1,"hero is a standalone star");
    reset();for(int i=0;i<AREA_MAX_SAMPLES;i++){sample(i+1,1,INFANTRY,500+(i%128)*.2f,(float)(i%128)*2);areaSamples[i].y=100+(i/128)*.2f;areaSamples[i].wy=(float)(i/128)*2;}
    drawOverlay(1,4800,vp);require(bfxOverlay.areas==1&&bfxOverlay.soldiers==AREA_MAX_SAMPLES&&!bfxOverlay.dropped,"dense army has one complete union without member-count splitting");
    require(vertexCount<=SYMBOL_VERTEX_CAPACITY,"bounded union geometry");
    reset();sample(1,1,INFANTRY,620,0);sample(2,1,ARCHER,680,100);areaSamples[0].y=areaSamples[1].y=798;
    drawOverlay(1,4800,vp);
    float hudTop=vp.height*(1-260.0f/768),hudRight=vp.width*(400.0f/1024);
    for(U32 i=0;i<vertexCount;i++)require(vertices[i].x>=hudRight||vertices[i].y<=hudTop,"areas cannot paint over the palantir");
    vertexCount=0;V2 a={900,760},b={1000,760},c={950,840};
    require(drawAreaTriangle(a,b,c,.24f,.24f,.24f,0x3298d0,vp,0),"clip a triangle across the HUD seam");
    for(U32 i=0;i<vertexCount;i++)require((vertices[i].color>>24)==61,"HUD clipping preserves opacity without an internal seam");
    reset();sample(1,1,INFANTRY,450,0);sample(2,1,INFANTRY,455,300);drawOverlay(.5f,4800,vp);
    require(bfxOverlay.areas==1,"projected footprints naturally fuse when they overlap");
    for(U32 i=0;i<vertexCount;i++)require(vertices[i].x==vertices[i].x&&vertices[i].y==vertices[i].y,"finite geometry");
    if(argc>1) {
        reset();U32 id=1;
        for(int block=0;block<3;block++)for(int y=0;y<5;y++)for(int x=0;x<9;x++) {
            sample(id++,block==2?2:1,x<4?INFANTRY:ARCHER,200+block*260+x*14,block*500+x*24);
            AreaSample &s=areaSamples[areaCount-1];s.y=260+y*15+(float)sin(x*.6f)*14;s.wy=y*25;
            s.color=block==2?0xf04444:0x3298d0;s.enemy=block==2;s.padding=7;
        }
        sample(id++,1,HERO,275,0);areaSamples[areaCount-1].y=215;
        sample(id++,2,HERO,795,1000);areaSamples[areaCount-1].y=215;areaSamples[areaCount-1].color=0xf04444;
        drawOverlay(1,4800,vp);dump(argv[1]);
    }
    puts("PASS: footprint unions, natural collisions, concavities, holes, subtle borders, motion, heroes and HUD clipping");return 0;
}
