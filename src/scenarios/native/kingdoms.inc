// Opt-in Eight Kingdoms staging. Uses the same verified factory/AI calls as battle.inc.
struct KingdomUnit { U32 player,horde,release; V3 position,destination; float angle; char name[64]; };
struct KingdomState {
    U32 stage,error,count,spawned,orders,alive,moved,casualties,members,initialMembers,enemyPairs;
    U32 players[8],owned[8];
    U32 completedBuildings,alliedPairs;
    U32 initialFrontMembers[4],frontMembers[4],frontMoved[4];
    U32 heavySpawned,heavyAlive,heavyMoved,heavyOrders;
};
extern "C" __declspec(dllexport) KingdomState bfxKingdoms={0};
extern "C" __declspec(dllexport) KingdomUnit bfxKingdomUnits[256]={0};
static U32 kingdomIds[256],kingdomStart;
static bool kingdomReleased[256];
static U32 kingdomMembers() {
    for(int f=0;f<4;f++)bfxKingdoms.frontMembers[f]=0;
    U32 count=0;void *obj=field<void*>(field<void*>(base,0x9FE78C),0xAC);
    for(int visited=0;obj&&visited<30000;obj=field<void*>(obj,0x8C),visited++) {
        if(field<U8>(obj,0x438)&1)continue;
        void *parent=field<void*>(obj,0x274);if(!parent)continue;
        U32 id=field<U32>(parent,0x74);
        for(U32 n=0;n<bfxKingdoms.count;n++)if(kingdomIds[n]==id){count++;bfxKingdoms.frontMembers[bfxKingdomUnits[n].player%4]++;break;}
    }
    return count;
}
extern "C" __declspec(dllexport) void bfxKingdomsStart() {
    if(bfxKingdoms.stage||!inMatch())return;
    bfxKingdoms.stage=1;
    if(!bfxKingdoms.count||bfxKingdoms.count>256){bfxKingdoms.error=1;return;}
    for(int p=0;p<8;p++)if(!bfxKingdoms.players[p]){bfxKingdoms.error=2;return;}
    for(int a=0;a<8;a++)for(int b=a+1;b<8;b++)if(a/4==b/4) {
        if(address<RelationshipFn>(0x2AD0C6)((void*)bfxKingdoms.players[a],0,field<void*>((void*)bfxKingdoms.players[b],0x2EC))!=2) {
            bfxKingdoms.error=5;return;
        }
        bfxKingdoms.alliedPairs++;
    }
    for(int pair=0;pair<4;pair++) {
        void *a=(void*)bfxKingdoms.players[pair],*b=(void*)bfxKingdoms.players[pair+4];
        if(address<RelationshipFn>(0x2AD0C6)(a,0,field<void*>(b,0x2EC))!=0){bfxKingdoms.error=3;return;}
        bfxKingdoms.enemyPairs++;
    }
    for(U32 n=0;n<bfxKingdoms.count;n++) {
        KingdomUnit &u=bfxKingdomUnits[n];
        if(u.player>=8){bfxKingdoms.error=4;return;}
        void *tmpl=battleTemplate(u.name);if(!tmpl){bfxKingdoms.error=100+n;return;}
        V3 pos=u.position;battleGround(pos);
        if(pos.z<75){bfxKingdoms.error=300+n;return;}
        U32 mask[4]={0,0,0,0};void *owner=(void*)bfxKingdoms.players[u.player];
        void *obj=address<NewObjectFn>(0x2D0A23)(field<void*>(base,0x9FF000),0,tmpl,field<void*>(owner,0x2EC),mask,false);
        if(!obj){bfxKingdoms.error=500+n;return;}
        address<PositionFn>(0x30AA80)(obj,0,&pos);address<FloatFn>(0x30AB9D)(obj,0,u.angle);
        if(u.horde==2) {
            address<BuiltFn>(0x2A9D02)(owner,0,0,obj,false);
            address<CameraFn>(0x28CBFD)(obj,0);
            if(field<float>(obj,0x280)==-1.0f)bfxKingdoms.completedBuildings++;
        }
        if(u.horde==1) {
            bool populated=false;void **modules=field<void**>(obj,0x244);
            for(int m=0;modules&&m<256&&modules[m];m++) {
                U32 *vt=field<U32*>(modules[m],0);
                if(vt==(U32*)(base+0x845050)&&vt[28]==(U32)(base+0x46E8EE)) {
                    ((CameraFn)vt[28])(modules[m],0);populated=true;break;
                }
            }
            if(!populated){bfxKingdoms.error=700+n;return;}
        }
        kingdomIds[n]=field<U32>(obj,0x74);u.position=pos;
        bfxKingdoms.spawned++;bfxKingdoms.owned[u.player]++;
        if(u.horde==3)bfxKingdoms.heavySpawned++;
    }
    for(int p=0;p<8;p++)address<RevealFn>(0x739790)(field<void*>(base,0x9FE74C),0,field<U32>((void*)bfxKingdoms.players[p],0x54));
    kingdomStart=field<U32>(field<void*>(base,0x9FE78C),0x40);
    bfxKingdoms.initialMembers=kingdomMembers();
    for(int f=0;f<4;f++)bfxKingdoms.initialFrontMembers[f]=bfxKingdoms.frontMembers[f];
    bfxKingdoms.stage=2;
    bfxBattalionSymbols.enabled=1;
}
extern "C" __declspec(dllexport) void bfxKingdomsProbe() {
    if(bfxKingdoms.stage!=2||!inMatch())return;
    void *logic=field<void*>(base,0x9FE78C);U32 elapsed=field<U32>(logic,0x40)-kingdomStart;
    bfxKingdoms.alive=bfxKingdoms.moved=0;
    bfxKingdoms.heavyAlive=bfxKingdoms.heavyMoved=0;
    for(int f=0;f<4;f++)bfxKingdoms.frontMoved[f]=0;
    for(U32 n=0;n<bfxKingdoms.count;n++) {
        void *obj=address<FindObjectFn>(0x49DC5)(logic,0,kingdomIds[n]);
        if(!obj||(field<U8>(obj,0x438)&1))continue;
        bfxKingdoms.alive++;KingdomUnit &u=bfxKingdomUnits[n];
        if(u.horde==3)bfxKingdoms.heavyAlive++;
        if(u.horde==2)continue;
        V3 p=field<V3>(obj,0x38);float dx=p.x-u.position.x,dy=p.y-u.position.y;
        if(dx*dx+dy*dy>75*75){bfxKingdoms.moved++;bfxKingdoms.frontMoved[u.player%4]++;if(u.horde==3)bfxKingdoms.heavyMoved++;}
        if(!kingdomReleased[n]&&elapsed>=u.release) {
            void *ai=field<void*>(obj,0x258);if(!ai)continue;
            V3 target=u.destination;battleGround(target);
            address<AttackMoveFn>(0x295A0F)((U8*)ai+0x20,0,&target,0x7fffffff,2);
            kingdomReleased[n]=true;bfxKingdoms.orders++;
            if(u.horde==3)bfxKingdoms.heavyOrders++;
        }
    }
    bfxKingdoms.members=kingdomMembers();
    bfxKingdoms.casualties=bfxKingdoms.initialMembers>bfxKingdoms.members?bfxKingdoms.initialMembers-bfxKingdoms.members:0;
}
