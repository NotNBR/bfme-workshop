// Optional, explicitly requested local battle preset. Native BFME objects,
// hordes, ownership, pathfinding and attack-move commands perform the battle.
struct BattleState {
    U32 stage,orcs,elves,orders,error,orcPlayer,elfPlayer,aliveOrcs,aliveElves;
    V3 center;
};
extern "C" __declspec(dllexport) BattleState bfxBattleState = {0};
static U32 battleIds[26];
typedef void* (__fastcall *NewObjectFn)(void*,void*,void*,void*,const U32*,bool);
typedef void* (__fastcall *FindTemplateFn)(void*,void*,const U32*);
typedef void (__fastcall *StringFn)(void*,void*,const char*);
typedef void (__fastcall *PositionFn)(void*,void*,const V3*);
typedef void (__fastcall *FloatFn)(void*,void*,float);
typedef float (__fastcall *GroundFn)(void*,void*,float,float,V3*);
typedef void (__fastcall *AttackMoveFn)(void*,void*,const V3*,int,int);
typedef void* (__fastcall *FindObjectFn)(void*,void*,U32);

static void *battleTemplate(const char *text) {
    U32 name=0;
    address<StringFn>(0x37BA0)(&name,0,text);
    void *result=address<FindTemplateFn>(0x2D06CA)(field<void*>(base,0x9FF000),0,&name);
    address<CameraFn>(0x36410)(&name,0);
    return result;
}
static void battleGround(V3 &position) {
    void *terrain=field<void*>(base,0x9FEC50);
    U32 *vt=field<U32*>(terrain,0);
    position.z=((GroundFn)vt[6])(terrain,0,position.x,position.y,0);
}
extern "C" __declspec(dllexport) void bfxStartBattle() {
    if(bfxBattleState.stage || !inMatch() || !activeView) return;
    bfxBattleState.stage=1; // never repeat a partially completed setup
    void *players=field<void*>(base,0x9FEEE8);
    void *local=field<void*>(players,0x10),*enemy=0;
    void *logic=field<void*>(base,0x9FE78C);
    // The two skirmish players have real defaults teams; exclude neutral/civilian.
    for(int i=0;i<20;i++) {
        void *player=field<void*>(players,0x18+4*i);
        if(player && player!=local && field<void*>(player,0x2EC) &&
           address<RelationshipFn>(0x2AD0C6)(local,0,field<void*>(player,0x2EC))==0) {
            enemy=player;break;
        }
    }
    if(!local||!enemy) {bfxBattleState.error=1;return;}
    void *templates[3]={battleTemplate("MordorFighterHorde"),
        battleTemplate("ElvenLorienWarriorHorde"),battleTemplate("ElvenLorienArcherHorde")};
    if(!templates[0]||!templates[1]||!templates[2]) {bfxBattleState.error=2;return;}
    bfxBattleState.orcPlayer=field<U32>(local,0x54);
    bfxBattleState.elfPlayer=field<U32>(enemy,0x54);
    V3 center=field<V3>(activeView,0xC);
    // Grey Mountains' open southern valley, north of the local starting fortress.
    center.y+=1100; battleGround(center);bfxBattleState.center=center;
    U32 mask[4]={0,0,0,0};
    for(int n=0;n<26;n++) {
        bool orc=n<16;int index=orc?n:n-16;
        void *player=orc?local:enemy;
        V3 position=center;
        position.x+=(index%4-1.5f)*180;
        position.y+=(orc?-1:1)*(240.0f+(index/4)*160);
        battleGround(position);
        void *object=address<NewObjectFn>(0x2D0A23)(field<void*>(base,0x9FF000),0,
            templates[orc?0:(index<5?1:2)],field<void*>(player,0x2EC),mask,false);
        if(!object) {bfxBattleState.error=3;return;}
        address<PositionFn>(0x30AA80)(object,0,&position);
        address<FloatFn>(0x30AB9D)(object,0,orc?1.570796327f:-1.570796327f);
        // Factory creation alone leaves an empty horde, which BFME removes on
        // its next update. Populate the native InitialPayload at the final
        // position, as the production/map-spawn paths do.
        bool populated=false;
        void **modules=field<void**>(object,0x244);
        for(int m=0;m<256 && modules[m];m++) {
            U32 *vt=field<U32*>(modules[m],0);
            if(vt==(U32*)(base+0x845050) && vt[28]==(U32)(base+0x46E8EE)) {
                ((CameraFn)vt[28])(modules[m],0);populated=true;break;
            }
        }
        if(!populated) {bfxBattleState.error=4;return;}
        battleIds[n]=field<U32>(object,0x74);
        if(orc)bfxBattleState.orcs++;else bfxBattleState.elves++;
    }
    address<PositionFn>(0x8D55D)(activeView,0,&center);
    address<FloatFn>(0x8D2B8)(activeView,0,1800.0f);
    bfxBattleState.stage=2;
}
extern "C" __declspec(dllexport) void bfxBattleOrders() {
    if(bfxBattleState.stage!=2 || !inMatch()) return;
    for(int n=0;n<26;n++) {
        void *object=address<FindObjectFn>(0x49DC5)(field<void*>(base,0x9FE78C),0,battleIds[n]);
        void *ai=object?field<void*>(object,0x258):0;
        if(!ai) continue;
        V3 destination=bfxBattleState.center;
        destination.x+=((n<16?n:n-16)%4-1.5f)*100;
        destination.y+=n<16?250:-250;
        battleGround(destination);
        address<AttackMoveFn>(0x295A0F)((U8*)ai+0x20,0,&destination,0x7fffffff,2);
        bfxBattleState.orders++;
    }
    bfxBattleState.stage=3;
}
extern "C" __declspec(dllexport) void bfxBattleProbe() {
    bfxBattleState.aliveOrcs=bfxBattleState.aliveElves=0;
    for(int n=0;n<26;n++) {
        void *obj=address<FindObjectFn>(0x49DC5)(field<void*>(base,0x9FE78C),0,battleIds[n]);
        if(obj && !(field<U8>(obj,0x438)&1)) {
            if(n<16)bfxBattleState.aliveOrcs++;else bfxBattleState.aliveElves++;
        }
    }
}
