// Grey Mountains scenario: native factions, resource bases and marching armies.
static const int ORC_COUNT=22, ARMY_COUNT=34, BUILDING_COUNT=16;
struct BattleState {
    U32 stage,orcs,elves,orders,error,orcPlayer,elfPlayer,aliveOrcs,aliveElves;
    V3 center;
    U32 fogDisabled,orcBuildings,elfBuildings,completeBuildings,unitsMoved,enemyVerified;
    U32 waves,reinforcementOrcs,reinforcementElves,openingCasualties,reinforcementsMoved,earlyCasualties;
    U32 orcHeroes,elfHeroes,heroOrders,aliveHeroes;
};
extern "C" __declspec(dllexport) BattleState bfxBattleState = {0};
static U32 battleIds[ARMY_COUNT],buildingIds[BUILDING_COUNT],heroIds[4];
static V3 initialArmy[ARMY_COUNT],basePositions[2],battleForward;
static void *battlePlayers[2];
static bool openingArmy[ARMY_COUNT],armyReleased[ARMY_COUNT];
static U32 battleStartFrame,openingMembers;
extern "C" __declspec(dllexport) U32 bfxReserveDebug[6]={0};
extern "C" __declspec(dllexport) void bfxBattleOrders();

typedef void* (__fastcall *NewObjectFn)(void*,void*,void*,void*,const U32*,bool);
typedef void* (__fastcall *FindTemplateFn)(void*,void*,const U32*);
typedef void (__fastcall *StringFn)(void*,void*,const char*);
typedef void (__fastcall *PositionFn)(void*,void*,const V3*);
typedef void (__fastcall *FloatFn)(void*,void*,float);
typedef float (__fastcall *GroundFn)(void*,void*,float,float,V3*);
typedef void (__fastcall *AttackMoveFn)(void*,void*,const V3*,int,int);
typedef void* (__fastcall *FindObjectFn)(void*,void*,U32);
typedef void (__fastcall *RevealFn)(void*,void*,int);
typedef int (__fastcall *CellShroudFn)(void*,void*,int,const V3*);
typedef void (__fastcall *BuiltFn)(void*,void*,void*,void*,bool);

static void *battleTemplate(const char *text) {
    U32 name=0;address<StringFn>(0x37BA0)(&name,0,text);
    void *result=address<FindTemplateFn>(0x2D06CA)(field<void*>(base,0x9FF000),0,&name);
    address<CameraFn>(0x36410)(&name,0);return result;
}
static void battleGround(V3 &p) {
    void *terrain=field<void*>(base,0x9FEC50);
    U32 *vt=field<U32*>(terrain,0);
    p.z=((GroundFn)vt[6])(terrain,0,p.x,p.y,0);
}
static V3 battleOffset(int side,float across,float forward) {
    float sign=side?-1.0f:1.0f;
    V3 p=basePositions[side];
    p.x+=sign*(battleForward.x*forward-battleForward.y*across);
    p.y+=sign*(battleForward.y*forward+battleForward.x*across);
    battleGround(p);return p;
}
static bool battlePlace(V3 &p,bool building,int side) {
    // Flat start-area ground, with separation from existing faction structures.
    // This preset is restricted to Grey Mountains by the launcher.
    V3 desired=p,best=p;float bestScore=1e20f;
    for(int ring=0;ring<=5;ring++) for(int n=0;n<(ring?8:1);n++) {
        float angle=n*.785398163f;V3 q=desired;
        q.x+=(float)cos(angle)*ring*85;q.y+=(float)sin(angle)*ring*85;
        if(q.x<180||q.x>4620||q.y<180||q.y>5220)continue;
        battleGround(q);
        if(fabs(q.z-basePositions[side].z)>25)continue;
        bool clear=true;float radius=building?65.0f:45.0f;
        for(int corner=0;corner<4;corner++) {
            V3 sample=q;sample.x+=(corner&1)?radius:-radius;sample.y+=(corner&2)?radius:-radius;
            battleGround(sample);if(fabs(sample.z-q.z)>8)clear=false;
        }
        if(!clear)continue;
        void *obj=field<void*>(field<void*>(base,0x9FE78C),0xAC);
        for(int count=0;obj&&count<20000;obj=field<void*>(obj,0x8C),count++) {
            void *tmpl=field<void*>(obj,4);
            if(!tmpl||!(field<U8>(tmpl,0x108)&0x80)||(field<U8>(obj,0x438)&1))continue;
            void *owner=address<OwnerFn>(0x28AFA9)(obj,0);
            if(owner!=battlePlayers[0]&&owner!=battlePlayers[1])continue;
            V3 existing=field<V3>(obj,0x38);
            float dx=q.x-existing.x,dy=q.y-existing.y,gap=building?180.0f:110.0f;
            if(dx*dx+dy*dy<gap*gap){clear=false;break;}
        }
        float score=ring*ring*7225.0f;
        if(clear&&score<bestScore){best=q;bestScore=score;}
    }
    if(bestScore==1e20f)return false;
    p=best;return true;
}
static void *battleCreate(void *tmpl,int side,const V3 &p,float angle) {
    U32 mask[4]={0,0,0,0};
    void *obj=address<NewObjectFn>(0x2D0A23)(field<void*>(base,0x9FF000),0,
        tmpl,field<void*>(battlePlayers[side],0x2EC),mask,false);
    if(obj) {
        address<PositionFn>(0x30AA80)(obj,0,&p);
        address<FloatFn>(0x30AB9D)(obj,0,angle);
    }
    return obj;
}
static U32 openingMemberCount() {
    U32 count=0;
    void *obj=field<void*>(field<void*>(base,0x9FE78C),0xAC);
    for(int visited=0;obj&&visited<20000;obj=field<void*>(obj,0x8C),visited++) {
        if(field<U8>(obj,0x438)&1)continue;
        void *parent=field<void*>(obj,0x274);if(!parent)continue;
        U32 id=field<U32>(parent,0x74);
        for(int n=0;n<ARMY_COUNT;n++)if(openingArmy[n]&&battleIds[n]==id){count++;break;}
    }
    return count;
}
static bool battleSend(int n) {
    void *object=address<FindObjectFn>(0x49DC5)(field<void*>(base,0x9FE78C),0,battleIds[n]);
    if(!object){bfxReserveDebug[1]++;return false;}
    if(field<U8>(object,0x438)&1){bfxReserveDebug[2]++;return false;}
    void *ai=field<void*>(object,0x258);if(!ai){bfxReserveDebug[3]++;return false;}
    int side=n>=ORC_COUNT;float sign=side?-1.0f:1.0f;
    V3 destination=bfxBattleState.center;
    destination.x+=sign*(battleForward.x*320-battleForward.y*((n%4)-1.5f)*100);
    destination.y+=sign*(battleForward.y*320+battleForward.x*((n%4)-1.5f)*100);
    battleGround(destination);
    address<AttackMoveFn>(0x295A0F)((U8*)ai+0x20,0,&destination,0x7fffffff,2);
    armyReleased[n]=true;bfxBattleState.orders++;return true;
}
extern "C" __declspec(dllexport) void bfxStartBattle() {
    if(bfxBattleState.stage||!inMatch()||!activeView)return;
    bfxBattleState.stage=1;
    battlePlayers[0]=field<void*>(field<void*>(base,0x9FEEE8),0x10);
    void *fortresses[2]={battleTemplate("MordorFortress"),battleTemplate("ElvenFortress")};
    bool found[2]={false,false};
    void *obj=field<void*>(field<void*>(base,0x9FE78C),0xAC);
    for(int count=0;obj&&count<20000;obj=field<void*>(obj,0x8C),count++) {
        void *owner=address<OwnerFn>(0x28AFA9)(obj,0),*tmpl=field<void*>(obj,4);
        if(tmpl==fortresses[0]&&owner==battlePlayers[0]){basePositions[0]=field<V3>(obj,0x38);found[0]=true;}
        if(tmpl==fortresses[1]&&owner&&owner!=battlePlayers[0]) {
            battlePlayers[1]=owner;basePositions[1]=field<V3>(obj,0x38);found[1]=true;
        }
    }
    // Use the actual Elven faction, not the map's hostile creep player.
    if(!found[0]||!found[1]){bfxBattleState.error=1;return;}
    if(address<RelationshipFn>(0x2AD0C6)(battlePlayers[0],0,field<void*>(battlePlayers[1],0x2EC))!=0){bfxBattleState.error=1;return;}
    bfxBattleState.enemyVerified=1;
    bfxBattleState.orcPlayer=field<U32>(battlePlayers[0],0x54);
    bfxBattleState.elfPlayer=field<U32>(battlePlayers[1],0x54);
    battleForward.x=basePositions[1].x-basePositions[0].x;
    battleForward.y=basePositions[1].y-basePositions[0].y;battleForward.z=0;
    float distance=(float)sqrt(battleForward.x*battleForward.x+battleForward.y*battleForward.y);
    if(distance<1500){bfxBattleState.error=5;return;}
    battleForward.x/=distance;battleForward.y/=distance;
    battleStartFrame=field<U32>(field<void*>(base,0x9FE78C),0x40);
    bfxBattleState.center=basePositions[0];
    bfxBattleState.center.x+=battleForward.x*distance*.5f;
    bfxBattleState.center.y+=battleForward.y*distance*.5f;battleGround(bfxBattleState.center);
    // Native ScriptActions reveal-map path uses TheShroudManager facade,
    // not ThePartitionManager (the recovered donor method names alias both).
    void *shroud=field<void*>(base,0x9FE74C);
    address<RevealFn>(0x739790)(shroud,0,bfxBattleState.orcPlayer);
    address<RevealFn>(0x739790)(shroud,0,bfxBattleState.elfPlayer);

    const char *buildings[2][8]={
        {"MordorSlaughterHouse","MordorSlaughterHouse","MordorSlaughterHouse","MordorOrcPit","MordorOrcPit","MordorHaradrimPalace","MordorTrollCage","MordorBattleTower"},
        {"ElvenMallornTree","ElvenMallornTree","ElvenMallornTree","ElvenBarracks","ElvenBarracks","ElvenGreenPasture","EregionForge","ElvenBattleTower"}};
    const float locations[8][2]={{-480,-220},{480,-220},{0,-520},{-320,140},{320,140},{-430,430},{430,430},{0,480}};
    for(int side=0;side<2;side++)for(int i=0;i<8;i++) {
        void *tmpl=battleTemplate(buildings[side][i]);
        if(!tmpl){bfxBattleState.error=2;return;}
        V3 p=battleOffset(side,locations[i][0],locations[i][1]);
        if(!battlePlace(p,true,side)){bfxBattleState.error=5;return;}
        float angle=(float)atan2(battleForward.y,battleForward.x)+(side?3.141592654f:0);
        void *building=battleCreate(tmpl,side,p,angle);
        if(!building){bfxBattleState.error=3;return;}
        // Factory buildings start complete (-1). Notify construction listeners
        // and register final-position pathfinding footprints.
        address<BuiltFn>(0x2A9D02)(battlePlayers[side],0,0,building,false);
        address<CameraFn>(0x28CBFD)(building,0);
        buildingIds[side*8+i]=field<U32>(building,0x74);
        if(side)bfxBattleState.elfBuildings++;else bfxBattleState.orcBuildings++;
    }
    const char *names[6]={"MordorFighterHorde","MordorArcherHorde","MordorEasterlingHorde",
        "ElvenLorienWarriorHorde","ElvenLorienArcherHorde","ElvenMithlondSentryHorde"};
    void *templates[6];
    for(int t=0;t<6;t++){templates[t]=battleTemplate(names[t]);if(!templates[t]){bfxBattleState.error=2;return;}}
    for(int n=0;n<ARMY_COUNT;n++) {
        int side=n>=ORC_COUNT,index=side?n-ORC_COUNT:n;
        int melee=side?6:16,archers=4;
        int role=index<melee?0:(index<melee+archers?1:2);
        float across,forward;
        openingArmy[n]=(role==0&&index<(side?4:8))||
            (role==1&&index-melee<2)||role==2;
        if(role==0){across=(index%4-1.5f)*165;forward=80+(index/4)*115.0f;}
        else if(role==1){across=(index-melee-.5f)*180;forward=330;}
        else {across=(index-melee-archers==0?-1:1)*420.0f;forward=160;}
        V3 p;
        if(openingArmy[n]) {
            float sign=side?-1.0f:1.0f;p=bfxBattleState.center;
            p.x+=sign*(-battleForward.x*forward-battleForward.y*across);
            p.y+=sign*(-battleForward.y*forward+battleForward.x*across);
            battleGround(p);
        } else {
            // Existing reserve battalions wait beyond their own production buildings.
            // They march in later; no units materialize at the fighting line.
            p=battleOffset(side,(index%4-1.5f)*165,780+(index%3)*135.0f);
        }
        if(!battlePlace(p,false,side)){bfxBattleState.error=5;return;}
        void *object=battleCreate(templates[side*3+role],side,p,(float)atan2(battleForward.y,battleForward.x)+(side?3.141592654f:0));
        if(!object){bfxBattleState.error=3;return;}
        bool populated=false;void **modules=field<void**>(object,0x244);
        for(int m=0;m<256&&modules[m];m++) {
            U32 *vt=field<U32*>(modules[m],0);
            if(vt==(U32*)(base+0x845050)&&vt[28]==(U32)(base+0x46E8EE)) {
                ((CameraFn)vt[28])(modules[m],0);populated=true;break;
            }
        }
        if(!populated){bfxBattleState.error=4;return;}
        battleIds[n]=field<U32>(object,0x74);initialArmy[n]=p;
        if(side)bfxBattleState.elves++;else bfxBattleState.orcs++;
    }
    const char *heroes[4]={"MordorWitchKing","MordorMouthOfSauron","ElvenHaldir","ElvenGlorfindel"};
    for(int h=0;h<4;h++) {
        int side=h/2;float sign=side?-1.0f:1.0f,across=(h%2?1.0f:-1.0f)*140;
        void *tmpl=battleTemplate(heroes[h]);
        if(!tmpl){bfxBattleState.error=2;return;}
        V3 p=bfxBattleState.center;
        p.x+=sign*(-battleForward.x*220-battleForward.y*across);
        p.y+=sign*(-battleForward.y*220+battleForward.x*across);
        battleGround(p);
        if(!battlePlace(p,false,side)){bfxBattleState.error=5;return;}
        void *hero=battleCreate(tmpl,side,p,(float)atan2(battleForward.y,battleForward.x)+(side?3.141592654f:0));
        if(!hero){bfxBattleState.error=3;return;}
        heroIds[h]=field<U32>(hero,0x74);
        if(side)bfxBattleState.elfHeroes++;else bfxBattleState.orcHeroes++;
    }
    address<PositionFn>(0x8D55D)(activeView,0,&bfxBattleState.center);
    address<FloatFn>(0x8D2B8)(activeView,0,2800.0f);
    openingMembers=openingMemberCount();
    bfxBattleState.stage=2;
    bfxBattleOrders();
}
extern "C" __declspec(dllexport) void bfxBattleOrders() {
    if(bfxBattleState.stage!=2||!inMatch())return;
    for(int n=0;n<ARMY_COUNT;n++) {
        if(openingArmy[n])battleSend(n);
    }
    for(int h=0;h<4;h++) {
        void *hero=address<FindObjectFn>(0x49DC5)(field<void*>(base,0x9FE78C),0,heroIds[h]);
        void *ai=hero?field<void*>(hero,0x258):0;
        if(!ai){bfxBattleState.error=6;return;}
        float sign=h<2?1.0f:-1.0f;V3 destination=bfxBattleState.center;
        destination.x+=sign*battleForward.x*220;
        destination.y+=sign*battleForward.y*220;battleGround(destination);
        address<AttackMoveFn>(0x295A0F)((U8*)ai+0x20,0,&destination,0x7fffffff,2);
        bfxBattleState.heroOrders++;
    }
    bfxBattleState.stage=3;
}
extern "C" __declspec(dllexport) void bfxBattleProbe() {
    bfxBattleState.aliveOrcs=bfxBattleState.aliveElves=bfxBattleState.unitsMoved=bfxBattleState.completeBuildings=0;
    void *logic=field<void*>(base,0x9FE78C);
    U32 members=openingMemberCount();
    bfxBattleState.openingCasualties=members<openingMembers?openingMembers-members:0;
    if(!bfxBattleState.waves)bfxBattleState.earlyCasualties=bfxBattleState.openingCasualties;
    U32 elapsed=field<U32>(logic,0x40)-battleStartFrame;
    if(bfxBattleState.stage==3&&bfxBattleState.waves<4&&elapsed>=40+bfxBattleState.waves*50) {
        int quota[2]={bfxBattleState.waves<2?3:2,1};
        for(int n=0;n<ARMY_COUNT;n++) {
            int side=n>=ORC_COUNT;
            if(openingArmy[n]){bfxReserveDebug[4]++;continue;}
            if(armyReleased[n]){bfxReserveDebug[5]++;continue;}
            if(quota[side]<=0)continue;
            bfxReserveDebug[0]++;
            if(battleSend(n)) {
                quota[side]--;
                if(side)bfxBattleState.reinforcementElves++;else bfxBattleState.reinforcementOrcs++;
            }
        }
        bfxBattleState.waves++;
    }
    bfxBattleState.reinforcementsMoved=0;
    for(int n=0;n<ARMY_COUNT;n++) {
        void *obj=address<FindObjectFn>(0x49DC5)(logic,0,battleIds[n]);
        if(obj&&!(field<U8>(obj,0x438)&1)) {
            if(n<ORC_COUNT)bfxBattleState.aliveOrcs++;else bfxBattleState.aliveElves++;
            V3 p=field<V3>(obj,0x38);float dx=p.x-initialArmy[n].x,dy=p.y-initialArmy[n].y;
            if(dx*dx+dy*dy>100*100) {
                bfxBattleState.unitsMoved++;
                if(!openingArmy[n]&&armyReleased[n])bfxBattleState.reinforcementsMoved++;
            }
        }
    }
    bfxBattleState.aliveHeroes=0;
    for(int h=0;h<4;h++) {
        void *hero=address<FindObjectFn>(0x49DC5)(logic,0,heroIds[h]);
        if(hero&&!(field<U8>(hero,0x438)&1))bfxBattleState.aliveHeroes++;
    }
    for(int i=0;i<BUILDING_COUNT;i++) {
        void *obj=address<FindObjectFn>(0x49DC5)(logic,0,buildingIds[i]);
        if(obj&&!(field<U8>(obj,0x438)&1)&&field<float>(obj,0x280)==-1.0f)bfxBattleState.completeBuildings++;
    }
    void *shroud=field<void*>(base,0x9FE74C);
    bfxBattleState.fogDisabled=
        address<CellShroudFn>(0x7397F0)(shroud,0,bfxBattleState.orcPlayer,&basePositions[1])==0 &&
        address<CellShroudFn>(0x7397F0)(shroud,0,bfxBattleState.elfPlayer,&basePositions[0])==0;
}
