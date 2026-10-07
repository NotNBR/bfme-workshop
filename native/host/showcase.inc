// Opt-in camera direction for the local gameplay recording. Normal play never enables it.
struct ShowcaseState { U32 enabled;float seconds;U32 finished; };
extern "C" __declspec(dllexport) ShowcaseState bfxShowcase = {0};
static LARGE_INTEGER showcaseStart;
static float showcaseAngle;
static void showcaseCamera(void *view) {
    if(!bfxShowcase.enabled||bfxShowcase.finished||bfxBattleState.stage!=3)return;
    LARGE_INTEGER now;QueryPerformanceCounter(&now);
    if(!showcaseStart.QuadPart){showcaseStart=now;showcaseAngle=field<float>(view,0x28);}
    float seconds=(float)((double)(now.QuadPart-showcaseStart.QuadPart)/timerFrequency.QuadPart);
    bfxShowcase.seconds=seconds;
    const float times[]={0,8,13,15,20,22,28,30};
    const float heights[]={600,600,2600,2600,7200,7200,600,600};
    if(seconds>=30){bfxShowcase.finished=1;return;}
    int segment=0;while(segment<6&&seconds>times[segment+1])segment++;
    float t=smooth((seconds-times[segment])/(times[segment+1]-times[segment]));
    float height=heights[segment]+(heights[segment+1]-heights[segment])*t;
    // Gentle opening arc, returning exactly to the original bearing/focus
    // with zero velocity at second 7, before either zoom-out stage starts.
    float arc=0;
    if(seconds>1&&seconds<7) {float wave=(float)sin((seconds-1)*3.141592654f/6);arc=wave*wave;}
    field<float>(view,0x28)=showcaseAngle+arc*.18f;
    V3 focus=bfxBattleState.center;
    focus.x+=arc*(-battleForward.y*95+battleForward.x*35);
    focus.y+=arc*(battleForward.x*95+battleForward.y*35);
    battleGround(focus);
    address<PositionFn>(0x8D55D)(view,0,&focus);
    address<FloatFn>(0x8D2B8)(view,0,height);
}
