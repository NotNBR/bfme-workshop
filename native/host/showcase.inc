// Opt-in camera direction for the local gameplay recording. Normal play never enables it.
struct ShowcaseState { U32 enabled;float seconds;U32 finished; };
extern "C" __declspec(dllexport) ShowcaseState bfxShowcase = {0};
static LARGE_INTEGER showcaseStart;
static void showcaseCamera(void *view) {
    if(!bfxShowcase.enabled||bfxShowcase.finished||bfxBattleState.stage!=3)return;
    LARGE_INTEGER now;QueryPerformanceCounter(&now);
    if(!showcaseStart.QuadPart)showcaseStart=now;
    float seconds=(float)((double)(now.QuadPart-showcaseStart.QuadPart)/timerFrequency.QuadPart);
    bfxShowcase.seconds=seconds;
    const float times[]={0,8,20,26,34,42,50,58,69,74};
    const float heights[]={600,600,3000,3000,7200,7200,2600,2600,650,650};
    if(seconds>=74){bfxShowcase.finished=1;return;}
    int segment=0;while(segment<8&&seconds>times[segment+1])segment++;
    float t=smooth((seconds-times[segment])/(times[segment+1]-times[segment]));
    float height=heights[segment]+(heights[segment+1]-heights[segment])*t;
    address<PositionFn>(0x8D55D)(view,0,&bfxBattleState.center);
    address<FloatFn>(0x8D2B8)(view,0,height);
}
