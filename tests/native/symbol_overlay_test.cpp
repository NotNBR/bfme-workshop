// Pure renderer/grouping regression; does not start or attach to BFME2.
#include <math.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include "../../src/native/common/types.inc"
template<class T> static T &field(void *p,int offset){return *(T*)((char*)p+offset);}
static const U32 SYMBOL_VERTEX_CAPACITY=262140;
static Vertex vertices[SYMBOL_VERTEX_CAPACITY];static U32 vertexCount;
struct { U32 buildings,units,icons; } bfxState;
struct { U32 selectedIcons,enemyIcons; } bfxSymbols;
static void tri(float ax,float ay,float bx,float by,float cx,float cy,U32 color){
    if(vertexCount+3>SYMBOL_VERTEX_CAPACITY){fprintf(stderr,"Triangle overflow\n");exit(1);}
    Vertex v[3]={{ax,ay,0,1,color},{bx,by,0,1,color},{cx,cy,0,1,color}};
    memcpy(vertices+vertexCount,v,sizeof(v));vertexCount+=3;
}
static void square(float x,float y,float r,U32 c){tri(x-r,y-r,x+r,y-r,x+r,y+r,c);tri(x-r,y-r,x+r,y+r,x-r,y+r,c);}
static void diamond(float x,float y,float r,U32 c){tri(x,y-r,x+r,y,x,y+r,c);tri(x,y-r,x,y+r,x-r,y,c);}
static U32 alpha(U32 c,float a){return (c&0xffffff)|((U32)(a*255)<<24);}
#include "../../projects/strategic/native/symbols.inc"
#include "../../projects/strategic/native/symbol_overlay.inc"
static void require(bool value,const char *message){if(!value){fprintf(stderr,"FAIL: %s\n",message);exit(1);}}
static void reset(){beginOverlay();memset(previousIds,0,sizeof(previousIds));vertexCount=0;}
static void sample(U32 id,U32 owner,SymbolKind kind,float x,float world=0,bool selected=false){
    SymbolSample &s=symbolSamples[sampleCount++];memset(&s,0,sizeof(s));s.id=id;s.owner=owner;s.kind=kind;
    s.x=x;s.y=100;s.wx=world;s.selected=selected;s.color=0x88aa44;
}
int main(){
    reset();sample(1,1,INFANTRY,100);sample(2,1,INFANTRY,110);sample(3,2,INFANTRY,100);
    sample(4,1,ARCHER,100);sample(5,1,HERO,100);sample(6,1,HERO,101);
    sample(7,1,INFANTRY,100,0,true);sample(8,1,INFANTRY,110,600);
    groupSymbols(30);require(clusterCount==7,"owner, role, hero, selection and world bounds");
    require(symbolClusters[0].seed.selected,"selected groups prioritized");
    reset();sample(1,1,INFANTRY,100);sample(2,1,INFANTRY,128);groupSymbols(30);require(clusterCount==1,"initial merge");
    symbolSamples[1].x=134;groupSymbols(30);require(clusterCount==1,"merge hysteresis");
    symbolSamples[1].x=138;groupSymbols(30);require(clusterCount==2,"split beyond hysteresis");
    groupSymbols(0);require(clusterCount==2,"near zoom retains battalions");
    reset();for(int i=0;i<130;i++)sample(i+1,1,INFANTRY,100);groupSymbols(30);
    require(clusterCount==3,"bounded cluster membership");
    reset();for(int i=0;i<4096;i++)sample(i+1,i+1,i==4095?HERO:INFANTRY,100);
    Viewport vp={0,0,1600,1200,0,1};drawOverlay(1,4800,vp);
    require(bfxOverlay.dropped>0&&symbolClusters[0].seed.kind==HERO,"overflow preserves hero priority");
    require(vertexCount<=SYMBOL_VERTEX_CAPACITY,"atomic marker budget");
    reset();sample(1,1,INFANTRY,400);sample(2,1,ARCHER,400);sample(3,2,INFANTRY,400);
    groupSymbols(30);placeMarkers(clusterCount,1,vp);
    require(symbolClusters[0].drawX==400&&symbolClusters[0].drawY==100,"first marker retains its anchor");
    require(symbolClusters[1].drawX!=400||symbolClusters[1].drawY!=100,"different roles fan out");
    require(symbolClusters[1].x==400&&symbolClusters[1].y==100,"footprint anchor does not move");
    reset();for(int i=0;i<64;i++){sample(i+1,1,INFANTRY,100+(i%8)*2);symbolSamples[i].y=100+(i/8)*2;}
    drawOverlay(1,4800,vp);require(bfxOverlay.merged==63&&vertexCount>100,"count badge and footprint drawing");
    for(U32 i=0;i<vertexCount;i++)require(vertices[i].x==vertices[i].x&&vertices[i].y==vertices[i].y,"finite footprint geometry");
    char object[0x300]={0},tmpl[0x140]={0};tmpl[0x108]|=128;
    tmpl[0x108+216/8]|=1<<(216%8);tmpl[0x108+54/8]|=1<<(54%8);
    require(emptyExpansionPad(tmpl),"empty fortress socket filtering");
    tmpl[0x108+54/8]&=~(1<<(54%8));require(!emptyExpansionPad(tmpl),"built expansions retained");
    tmpl[0x108+216/8]&=~(1<<(216%8));
    const int bits[]={17,63,196,64,49,203,189};
    const SymbolKind expected[]={FORTRESS,PRODUCTION,ECONOMY,DEFENSE,OBJECTIVE,GATE,WALL};
    for(int j=0;j<7;j++){tmpl[0x108+bits[j]/8]|=1<<(bits[j]%8);require(symbolKind(object,tmpl)==expected[j],"building category");tmpl[0x108+bits[j]/8]&=~(1<<(bits[j]%8));}
    tmpl[0x108+28/8]|=1<<(28%8);tmpl[0x108+196/8]|=1<<(196%8);
    require(symbolKind(object,tmpl)==ECONOMY,"Gondor farm CASTLE_KEEP flag is not a fortress");
    tmpl[0x108+196/8]&=~(1<<(196%8));tmpl[0x108+177/8]|=1<<(177%8);
    require(symbolKind(object,tmpl)==FORTRESS,"base keep retains fortress category");
    puts("PASS: grouping, owner/visibility-domain inputs, priorities, hysteresis, capacity, footprints, building categories");return 0;
}
