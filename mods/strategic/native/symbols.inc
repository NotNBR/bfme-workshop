// BFME2 KindOf indices verified in the retail table at VA 0xDBBE18 and
// openbfme2/Code/GameEngine/Source/GameLogic/ScriptEngine/KindOfGetNameFromSingleBit.cpp.
// Keep the first ten telemetry slots ABI-compatible with existing capture tools.
enum SymbolKind { BUILDING, INFANTRY, ARCHER, PIKE, CAVALRY, SIEGE, MONSTER, HERO, BUILDER, AIR, SYMBOL_KINDS,
    FORTRESS, PRODUCTION, ECONOMY, DEFENSE, OBJECTIVE, GATE, WALL };
static bool buildingKind(SymbolKind kind) { return kind==BUILDING||kind>=FORTRESS; }
struct SymbolTypes { U32 current[SYMBOL_KINDS],peak[SYMBOL_KINDS]; };
extern "C" __declspec(dllexport) SymbolTypes bfxSymbolTypes = {0};
static bool hasKind(void *tmpl,int bit) {
    return (field<U8>(tmpl,0x108+bit/8)&(1<<(bit%8)))!=0;
}
static bool emptyExpansionPad(void *tmpl) { return hasKind(tmpl,216)&&hasKind(tmpl,54); }
static SymbolKind symbolKind(void *obj,void *tmpl) {
    if(hasKind(tmpl,7)) {
        if(hasKind(tmpl,203)||hasKind(tmpl,137))return GATE;
        // CASTLE_KEEP alone also appears on Gondor farms and civilian buildings.
        if(hasKind(tmpl,17)||hasKind(tmpl,18)||(hasKind(tmpl,28)&&hasKind(tmpl,177)))return FORTRESS;
        if(hasKind(tmpl,64)||(hasKind(tmpl,150)&&hasKind(tmpl,3)))return DEFENSE;
        if(hasKind(tmpl,189)||hasKind(tmpl,61)||hasKind(tmpl,156))return WALL;
        if(hasKind(tmpl,196)||hasKind(tmpl,135))return ECONOMY;
        if(hasKind(tmpl,49))return OBJECTIVE;
        if(hasKind(tmpl,63)||hasKind(tmpl,69))return PRODUCTION;
        return BUILDING;
    }
    // Banner bearers share their battalion's tactical role.
    void *parent=field<void*>(obj,0x274);
    if(parent) {
        void *parentTemplate=field<void*>(parent,4);
        if(parentTemplate&&hasKind(parentTemplate,109))tmpl=parentTemplate;
    }
    if(hasKind(tmpl,90)||hasKind(tmpl,190))return HERO;
    if(hasKind(tmpl,14)||hasKind(tmpl,143))return BUILDER;
    if(hasKind(tmpl,12)||hasKind(tmpl,207))return AIR;
    if(hasKind(tmpl,9))return CAVALRY;
    if(hasKind(tmpl,198))return PIKE;
    if(hasKind(tmpl,133))return ARCHER;
    if(hasKind(tmpl,11)||hasKind(tmpl,93)||hasKind(tmpl,139))return SIEGE;
    if(hasKind(tmpl,10)||hasKind(tmpl,171))return MONSTER;
    return INFANTRY;
}
static void iconPolygon(float x,float y,float radius,const V2 *points,int count,U32 color) {
    for(int i=0;i<count;i++) {
        int next=(i+1)%count;
        tri(x,y,x+points[i].x*radius,y+points[i].y*radius,
            x+points[next].x*radius,y+points[next].y*radius,color);
    }
}
static void iconLine(float x1,float y1,float x2,float y2,float width,U32 color) {
    float dx=x2-x1,dy=y2-y1,length=(float)sqrt(dx*dx+dy*dy);
    if(length<.01f)return;
    float px=-dy*width*.5f/length,py=dx*width*.5f/length;
    tri(x1+px,y1+py,x2+px,y2+py,x2-px,y2-py,color);
    tri(x1+px,y1+py,x2-px,y2-py,x1-px,y1-py,color);
}
static void tacticalSymbol(SymbolKind kind,float x,float y,bool selected,U32 fill,U32 rim,U32 ink,U32 dark) {
    static const V2 house[]={{-1,1},{1,1},{1,-.25f},{0,-1},{-1,-.25f}};
    static const V2 infantry[]={{0,-1},{1,0},{0,1},{-1,0}};
    static const V2 archer[]={{0,-1},{1,.85f},{-1,.85f}};
    static const V2 pike[]={{0,-1.15f},{.65f,.05f},{.65f,1},{-.65f,1},{-.65f,.05f}};
    static const V2 cavalry[]={{-.9f,-.9f},{.15f,-.9f},{1,0},{.15f,.9f},{-.9f,.9f},{-.25f,0}};
    static const V2 siege[]={{-1,-.7f},{1,-.7f},{1,.7f},{-1,.7f}};
    static const V2 hexagon[]={{0,-1},{.87f,-.5f},{.87f,.5f},{0,1},{-.87f,.5f},{-.87f,-.5f}};
    static const V2 star[]={{0,-1},{.26f,-.36f},{.95f,-.31f},{.42f,.14f},{.59f,.81f},
        {0,.44f},{-.59f,.81f},{-.42f,.14f},{-.95f,-.31f},{-.26f,-.36f}};
    static const V2 wings[]={{0,-1},{1,.5f},{.3f,.3f},{0,1},{-.3f,.3f},{-1,.5f}};
    const V2 *shape=infantry;int count=4;
    switch(kind) {
        case BUILDING:shape=house;count=5;break;
        case ARCHER:shape=archer;count=3;break;
        case PIKE:shape=pike;count=5;break;
        case CAVALRY:shape=cavalry;count=6;break;
        case SIEGE:shape=siege;break;
        case MONSTER:case BUILDER:shape=hexagon;count=6;break;
        case HERO:shape=star;count=10;break;
        case AIR:shape=wings;count=6;break;
    }
    U32 firstVertex=vertexCount;
    float outer=selected?8.5f:7.5f,inner=selected?7.25f:6.0f;
    iconPolygon(x,y,outer,shape,count,dark);
    iconPolygon(x,y,inner,shape,count,rim);
    iconPolygon(x,y,4.5f,shape,count,fill);
    // A few broad strokes remain legible at strategic distances.
    switch(kind) {
        case BUILDING:
            iconLine(x-2,y+3,x-2,y-.5f,1.2f,ink);iconLine(x+2,y+3,x+2,y-.5f,1.2f,ink);
            iconLine(x-2,y-.5f,x+2,y-.5f,1.2f,ink);break;
        case INFANTRY:
            iconLine(x-2,y-2,x+2,y+2,1.2f,ink);iconLine(x+2,y-2,x-2,y+2,1.2f,ink);break;
        case ARCHER:
            iconLine(x,y+2,x,y-1.5f,1.2f,ink);tri(x-1.8f,y,x,y-2,x+1.8f,y,ink);break;
        case PIKE:
            iconLine(x,y+3,x,y-3,1.4f,ink);break;
        case CAVALRY:
            iconLine(x-1,y-2,x+1.5f,y,1.3f,ink);iconLine(x+1.5f,y,x-1,y+2,1.3f,ink);break;
        case SIEGE:
            iconLine(x-2.5f,y,x+2.5f,y,1.5f,ink);
            square(x-2,y+3,.8f,ink);square(x+2,y+3,.8f,ink);break;
        case MONSTER:
            iconLine(x-2,y-2,x-2,y+2,1.1f,ink);iconLine(x,y-2,x,y+2,1.1f,ink);
            iconLine(x+2,y-2,x+2,y+2,1.1f,ink);break;
        case BUILDER:
            iconLine(x,y+3,x,y-2,1.3f,ink);iconLine(x-2.5f,y-2,x+2.5f,y-2,2,ink);break;
        case HERO:case AIR:break;
    }
    // Scale every contour and glyph together, keeping the symbol centered.
    float scale=1.12f*(kind==HERO?1.4f:1.0f);
    for(U32 v=firstVertex;v<vertexCount;v++) {
        vertices[v].x=x+(vertices[v].x-x)*scale;
        vertices[v].y=y+(vertices[v].y-y)*scale;
    }
    bfxSymbolTypes.current[kind]++;
}
