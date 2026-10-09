// Pure bounded grouping policy: no game memory reads or graphics calls.
static const int MAX_SYMBOLS=4096, SYMBOL_HASH_SIZE=8192;
struct SymbolSample {
    U32 id,owner,color,previous;
    SymbolKind kind;
    bool selected,enemy;
    float x,y,wx,wy,wallX,wallY;
};
struct SymbolGroup {
    SymbolSample seed;
    U32 count;
    int members[64];
    float x,y,drawX,drawY;
};
static SymbolSample symbolSamples[MAX_SYMBOLS];
static SymbolGroup symbolClusters[MAX_SYMBOLS];
static U32 seenSymbols[SYMBOL_HASH_SIZE],previousIds[SYMBOL_HASH_SIZE],previousSeeds[SYMBOL_HASH_SIZE];
static int sampleCount,clusterCount;
static int symbolSlot(U32 *keys,U32 id) {
    U32 slot=(id*2654435761u)&(SYMBOL_HASH_SIZE-1);
    while(keys[slot]&&keys[slot]!=id)slot=(slot+1)&(SYMBOL_HASH_SIZE-1);
    return (int)slot;
}
static int compareSample(const void *a,const void *b) {
    U32 x=((const SymbolSample*)a)->id,y=((const SymbolSample*)b)->id;
    return x<y?-1:x>y?1:0;
}
static int symbolPriority(const SymbolSample &s) {
    if(s.selected)return 6;
    if(s.kind==HERO)return 5;
    if(s.kind==FORTRESS||s.kind==OBJECTIVE)return 4;
    if(s.kind==SIEGE||s.kind==MONSTER||s.kind==GATE||s.kind==DEFENSE)return 3;
    if(s.kind==WALL)return 0;
    return buildingKind(s.kind)?1:2;
}
static int compareCluster(const void *a,const void *b) {
    const SymbolGroup &x=*(const SymbolGroup*)a,&y=*(const SymbolGroup*)b;
    int p=symbolPriority(y.seed)-symbolPriority(x.seed);
    return p?p:compareSample(&x.seed,&y.seed);
}
static void groupSymbols(float radius) {
    qsort(symbolSamples,sampleCount,sizeof(SymbolSample),compareSample);
    clusterCount=0;
    for(int i=0;i<sampleCount;i++) {
        SymbolSample &s=symbolSamples[i];int best=-1;float bestDistance=1e20f;
        int slot=symbolSlot(previousIds,s.id);
        s.previous=previousIds[slot]==s.id?previousSeeds[slot]:0;
        if(radius>0&&!buildingKind(s.kind)&&s.kind!=HERO&&s.kind!=BUILDER) {
            for(int g=0;g<clusterCount;g++) {
                SymbolGroup &c=symbolClusters[g];
                if(c.count>=64||c.seed.owner!=s.owner||c.seed.kind!=s.kind||c.seed.selected!=s.selected)continue;
                float dx=s.x-c.seed.x,dy=s.y-c.seed.y,wx=s.wx-c.seed.wx,wy=s.wy-c.seed.wy;
                float limit=radius+(s.previous==c.seed.id?6.0f:0.0f),d=dx*dx+dy*dy;
                // Anchor bounds prevent transitive chains swallowing separate fronts.
                if(d<=limit*limit&&wx*wx+wy*wy<=480*480&&d<bestDistance){best=g;bestDistance=d;}
            }
        }
        if(best<0) {
            best=clusterCount++;SymbolGroup &c=symbolClusters[best];
            c.seed=s;c.count=0;c.x=c.y=0;
        }
        SymbolGroup &c=symbolClusters[best];c.members[c.count++]=i;c.x+=s.x;c.y+=s.y;
    }
    memset(previousIds,0,sizeof(previousIds));
    for(int g=0;g<clusterCount;g++) {
        SymbolGroup &c=symbolClusters[g];c.x/=c.count;c.y/=c.count;c.drawX=c.x;c.drawY=c.y;
        for(U32 j=0;j<c.count;j++) {
            U32 id=symbolSamples[c.members[j]].id;int slot=symbolSlot(previousIds,id);
            previousIds[slot]=id;previousSeeds[slot]=c.seed.id;
        }
    }
    qsort(symbolClusters,clusterCount,sizeof(SymbolGroup),compareCluster);
}
static void placeMarkers(int admitted,float scale,const Viewport &vp) {
    // Small, deterministic fan-out. Ground footprints keep their real positions.
    const float offsets[][2]={{0,0},{0,-38},{30,0},{-30,0},{0,38},{30,-32},{-30,-32},{30,32},{-30,32}};
    for(int i=0;i<admitted;i++) {
        SymbolGroup &c=symbolClusters[i];if(c.seed.kind==WALL)continue;
        for(int p=0;p<9;p++) {
            float x=c.x+offsets[p][0]*scale,y=c.y+offsets[p][1]*scale;
            float bottom=y+(c.count>1?29:15)*scale;
            if(x<vp.x+16*scale||x>vp.x+vp.width-16*scale||y<vp.y+16*scale||bottom>vp.y+vp.height)continue;
            if(bottom>vp.y+vp.height*(1-260.0f/768)&&x-16*scale<vp.x+vp.width*(400.0f/1024))continue;
            bool clear=true;
            for(int j=0;j<i;j++) {
                const SymbolGroup &other=symbolClusters[j];if(other.seed.kind==WALL)continue;
                if(fabs(x-other.drawX)<29*scale&&y-15*scale<other.drawY+(other.count>1?29:15)*scale&&bottom>other.drawY-15*scale){clear=false;break;}
            }
            if(clear){c.drawX=x;c.drawY=y;break;}
        }
    }
}
