// GPL-3.0-only. BFME2 1.06 integration; addresses checked against openbfme2.
// This DLL is loaded by our version-guarded launcher into the isolated game.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <math.h>
#include <float.h>
#include <string.h>

typedef unsigned char U8;
typedef unsigned int U32;
struct V3 { float x,y,z; };
struct V2 { float x,y; };
struct I2 { int x,y; };
struct Matrix { float m[3][4]; };
struct Vertex { float x,y,z,rhw; U32 color; };
struct Viewport { U32 x,y,width,height; float minZ,maxZ; };
struct State {
    U32 version, installed, faults, cameraCalls, drawCalls, icons, buildings, units;
    U32 hiddenSkipped, projection, transitions, pickCalls;
    float height, blend, halfWidth, halfHeight;
    U32 lastError;
    U32 probeCalls;
    float pickPixelError, parallelRayError;
    U32 frameUpdates, healthCalls;
    float renderHeight, maxBlendStep, nativeBarWidth, scaledBarWidth;
};
extern "C" __declspec(dllexport) State bfxState = {2};
struct SymbolState {
    U32 samples, interpolatedPositions, betweenLogicMoves, logicMoves;
    U32 selectedIcons, enemyIcons, peakSelectedIcons, peakEnemyIcons;
};
extern "C" __declspec(dllexport) SymbolState bfxSymbols = {0};
static U32 symbolObject, symbolLogicFrame;
static V3 symbolPosition;
struct CameraSample {
    volatile U32 sequence;
    U32 phase,frame,projection;
    float seconds,targetHeight,currentHeight,terrainHeight,zoom,blend,filteredHeight;
    V3 focus,position,back;
    float elevation,planeLeft,planeBottom,planeRight,planeTop,nearClip,farClip;
    float nativeBarWidth,scaledBarWidth;
};
struct CameraTrace { volatile U32 count; CameraSample samples[4096]; };
extern "C" __declspec(dllexport) CameraTrace bfxTrace = {0};
static LARGE_INTEGER traceStart;
static U8 *base;
static void *cameraOriginal, *pickOriginal, *endOriginal;
static void *updateOriginal, *healthOriginal;
static void *activeView;
static bool wasOrtho;
static bool filterReady;
static float renderHeight, tilt, tiltVelocity;
static LARGE_INTEGER lastCameraTime, timerFrequency;
static Vertex vertices[65532];
static U32 vertexCount;
template<class T> T &field(void *p, U32 offset) { return *(T*)((U8*)p+offset); }
template<class T> T address(U32 rva) { return (T)(base+rva); }
typedef void (__fastcall *CameraFn)(void*,void*);
typedef void (__fastcall *TransformFn)(void*,void*,const Matrix*);
typedef void (__fastcall *PlaneFn)(void*,void*,const V2*,const V2*);
typedef void (__fastcall *PickFn)(void*,void*,const I2*,V3*,V3*);
typedef void (__cdecl *EndFn)(bool);
typedef void* (__fastcall *OwnerFn)(void*,void*);
typedef bool (__fastcall *SelectableFn)(void*,void*);
typedef int (__fastcall *ShroudFn)(void*,void*,int);
typedef int (__fastcall *ProjectFn)(void*,void*,V3*,const V3*);
typedef U32 (__fastcall *ColorFn)(void*,void*);
typedef int (__fastcall *IntFn)(void*,void*);
typedef const Matrix* (__fastcall *DrawableTransformFn)(void*,void*);
typedef int (__fastcall *RelationshipFn)(void*,void*,void*);

static bool inMatch() {
    void *logic=field<void*>(base,0x9FE78C);
    return logic && field<int>(logic,0x110)==2;
}
// 0: before native view update, 1: native camera just built,
// 2: after view update, 3: actual rendered frame. No disk IO on the game thread.
static void traceCamera(void *view,U32 phase) {
    if(!view || view!=field<void*>(base,0x9FEA3C) || !inMatch()) return;
    void *cam=field<void*>(view,0x104);
    if(!cam) return;
    LARGE_INTEGER now;QueryPerformanceCounter(&now);
    if(!traceStart.QuadPart) traceStart=now;
    U32 sequence=bfxTrace.count+1;
    CameraSample &sample=bfxTrace.samples[(sequence-1)%4096];
    sample.sequence=0;
    sample.phase=phase;sample.frame=bfxState.frameUpdates;
    sample.projection=field<U32>(cam,0xC4);
    sample.seconds=(float)((double)(now.QuadPart-traceStart.QuadPart)/timerFrequency.QuadPart);
    sample.targetHeight=field<float>(view,0x40);
    sample.currentHeight=field<float>(view,0x50);
    sample.terrainHeight=field<float>(view,0x54);
    sample.zoom=field<float>(view,0x3C);
    sample.blend=tilt;sample.filteredHeight=renderHeight;
    sample.focus=field<V3>(view,0x0C);
    Matrix &m=field<Matrix>(cam,0x18);
    sample.position.x=m.m[0][3];sample.position.y=m.m[1][3];sample.position.z=m.m[2][3];
    sample.back.x=m.m[0][2];sample.back.y=m.m[1][2];sample.back.z=m.m[2][2];
    float sine=sample.back.z;if(sine>1)sine=1;if(sine< -1)sine=-1;
    sample.elevation=(float)asin(sine)*57.2957795f;
    V2 lo=field<V2>(cam,0xD8),hi=field<V2>(cam,0xE0);
    sample.planeLeft=lo.x;sample.planeBottom=lo.y;sample.planeRight=hi.x;sample.planeTop=hi.y;
    sample.nearClip=field<float>(cam,0xEC);sample.farClip=field<float>(cam,0xF0);
    sample.nativeBarWidth=bfxState.nativeBarWidth;sample.scaledBarWidth=bfxState.scaledBarWidth;
    sample.sequence=sequence;bfxTrace.count=sequence;
}
static float smooth(float value) {
    if(value<=0) return 0;
    if(value>=1) return 1;
    return value*value*(3-2*value);
}
// Exact critically damped step: independent of frame rate, with continuous
// velocity when the wheel reverses. A stalled render must not skip the tween.
static void damp(float target,float dt,float rate,float &value,float &velocity) {
    float delta=value-target,term=(velocity+rate*delta)*dt;
    float decay=(float)exp(-rate*dt);
    value=target+(delta+term)*decay;
    velocity=(velocity-rate*term)*decay;
    if(fabs(value-target)<.0001f && fabs(velocity)<.001f) {value=target;velocity=0;}
}
static void advanceCamera(void *view) {
    LARGE_INTEGER now;QueryPerformanceCounter(&now);
    // Use the last native transform's measured height. +0x40 is the wheel's
    // target; +0x50 is the previous frame's height during native interpolation.
    float height=renderHeight>0?renderHeight:field<float>(view,0x50);
    if(!_finite(height) || height<=0) {filterReady=false;return;}
    renderHeight=height;
    float target=smooth((height-800.0f)/1800.0f);
    if(!filterReady) {
        tilt=target;tiltVelocity=0;
        filterReady=true;
    } else {
        float dt=(float)((double)(now.QuadPart-lastCameraTime.QuadPart)/timerFrequency.QuadPart);
        if(dt>.05f) dt=.05f;
        if(dt<0) dt=0;
        float previous=tilt;
        // ~0.26 s to cover 95% of a step (was ~0.59 s at rate 8).
        // Zoom already has native easing, so keep this extra tilt response short.
        damp(target,dt,18,tilt,tiltVelocity);
        float step=(float)fabs(tilt-previous);
        if(step>bfxState.maxBlendStep) bfxState.maxBlendStep=step;
    }
    lastCameraTime=now;
    bfxState.renderHeight=renderHeight;
}
static void strategicCamera(void *view) {
    if(view!=field<void*>(base,0x9FEA3C)) {
        ((CameraFn)cameraOriginal)(view,0);return;
    }
    void *cam=field<void*>(view,0x104);
    if(!cam) return;
    // Native code resets its view plane every camera update. Reset projection
    // before delegating so the close view is exactly the game's own transform.
    field<U32>(cam,0xC4)=0;
    field<U8>(cam,0xFC)=0;
    ((CameraFn)cameraOriginal)(view,0);
    traceCamera(view,1);
    bfxState.cameraCalls++;
    activeView=view;
    const float requested=field<float>(view,0x40);
    Matrix mat=field<Matrix>(cam,0x18);
    // buildCameraTransform interpolates before +0x50 is updated. Measure the
    // resulting native transform above its focus plane, not either input field.
    const float height=mat.m[2][3]-field<float>(view,0x14);
    if(!_finite(height) || height<=0) {filterReady=false;return;}
    renderHeight=height;bfxState.renderHeight=height;
    bool playing=inMatch();
    if(playing && !filterReady) advanceCamera(view);
    const float blend=playing?tilt:0;
    bfxState.height=requested; bfxState.blend=blend;
    if(!playing || !filterReady || blend<=0) {
        if(!playing) filterReady=false;
        if(wasOrtho) bfxState.transitions++;
        wasOrtho=false; bfxState.projection=0; return;
    }
    float rightX=mat.m[0][0],rightY=mat.m[1][0];
    float len=(float)sqrt(rightX*rightX+rightY*rightY);
    if(!_finite(len) || !_finite(mat.m[2][2]) || len<.1f || mat.m[2][2]<.05f) return;
    rightX/=len;rightY/=len;
    float z=mat.m[2][3];
    float distance=height/mat.m[2][2];
    V3 focus={mat.m[0][3]-mat.m[0][2]*distance,
              mat.m[1][3]-mat.m[1][2]*distance,z-height};
    float elevation=(float)asin(mat.m[2][2]>.99999f?.99999f:mat.m[2][2]);
    elevation+=(1.570796327f-elevation)*blend;
    float s=(float)sin(elevation),c=(float)cos(elevation);
    mat.m[0][0]=rightX;mat.m[1][0]=rightY;mat.m[2][0]=0;
    mat.m[0][1]=-rightY*s;mat.m[1][1]=rightX*s;mat.m[2][1]=c;
    mat.m[0][2]=rightY*c;mat.m[1][2]=-rightX*c;mat.m[2][2]=s;
    bool ortho=blend>=1;
    // Approach parallel projection before switching mode. Keeping view-plane
    // extent * distance constant avoids a scale pop at the orthographic edge.
    float perspective=ortho?1:1-.875f*smooth((blend-.65f)/.35f);
    float cameraHeight=height/perspective;
    distance=cameraHeight/s;
    mat.m[0][3]=focus.x+mat.m[0][2]*distance;
    mat.m[1][3]=focus.y+mat.m[1][2]*distance;
    mat.m[2][3]=focus.z+cameraHeight;
    if(ortho) {
        V2 lo=field<V2>(cam,0xD8),hi=field<V2>(cam,0xE0);
        lo.x*=height;lo.y*=height;hi.x*=height;hi.y*=height;
        address<PlaneFn>(0x134020)(cam,0,&lo,&hi);
        field<U32>(cam,0xC4)=1;
        bfxState.halfWidth=(hi.x-lo.x)*.5f;
        bfxState.halfHeight=(hi.y-lo.y)*.5f;
    } else if(perspective<1) {
        V2 lo=field<V2>(cam,0xD8),hi=field<V2>(cam,0xE0);
        lo.x*=perspective;lo.y*=perspective;hi.x*=perspective;hi.y*=perspective;
        address<PlaneFn>(0x134020)(cam,0,&lo,&hi);
        field<float>(cam,0xF0)+=cameraHeight-height;
    }
    address<TransformFn>(0x13B790)(cam,0,&mat);
    field<U8>(cam,0xFC)=0;
    if(ortho!=wasOrtho) bfxState.transitions++;
    wasOrtho=ortho;bfxState.projection=ortho?1:0;
}
static void __fastcall cameraHook(void *view,void*) {
    strategicCamera(view);
}
static void showcaseCamera(void *view);
static void __fastcall updateHook(void *view,void*) {
    bool tactical=view==field<void*>(base,0x9FEA3C);
    if(tactical) traceCamera(view,0);
    if(tactical && inMatch()) {showcaseCamera(view);advanceCamera(view);}
    U32 calls=bfxState.cameraCalls;
    ((CameraFn)updateOriginal)(view,0);
    // Native updates can skip setCameraTransform when no input has changed.
    // Continue easing on those frames, before reflections/culling/UI projection.
    if(tactical && filterReady && calls==bfxState.cameraCalls &&
       (tiltVelocity!=0 || fabs(tilt-bfxState.blend)>.00001f ||
        (tilt>=1 && bfxState.projection!=1) || (tilt<=0 && bfxState.projection!=0)))
        strategicCamera(view);
    if(tactical) {bfxState.frameUpdates++;traceCamera(view,2);}
}
static void scaleHealth(void *drawable) {
    if(!inMatch() || !filterReady || !activeView || renderHeight<=0) return;
    int *region=&field<int>(drawable,0x460);
    int width=region[2]-region[0];
    if(width<=0 || region[3]<=region[1]) return;
    // Undo the stock rectangle's 1/getZoom factor before applying actual
    // camera height. Extended map max height changes getZoom's reference scale.
    float nativeZoom=field<float>(activeView,0xA8)*field<float>(activeView,0x3C);
    float scaled=width*nativeZoom*300.0f/renderHeight;
    float cap=240.0f+(36.0f-240.0f)*smooth((renderHeight-300.0f)/1100.0f);
    if(scaled>cap) scaled=cap;
    if(scaled<12) scaled=12;
    if(scaled>width) scaled=(float)width;
    int newWidth=(int)(scaled+.5f);
    int anchor=region[0]+(int)(width*.45f);
    region[0]=anchor-(int)(newWidth*.45f);region[2]=region[0]+newWidth;
    bfxState.healthCalls++;
    bfxState.nativeBarWidth=(float)width;bfxState.scaledBarWidth=(float)newWidth;
}
typedef void (__fastcall *QueueFn)(void*,void*,int,void*);
static void __fastcall healthHook(void *client,void*,int kind,void *drawable) {
    // Queue 0 follows a freshly calculated health rectangle. Hooking the whole
    // prepare function would rescale stale rectangles on its early-out paths.
    if(kind==0 && drawable) scaleHealth(drawable);
    ((QueueFn)healthOriginal)(client,0,kind,drawable);
}
static void __fastcall pickHook(void *view,void*,const I2 *screen,V3 *start,V3 *end) {
    void *cam=field<void*>(view,0x104);
    if(!cam || field<U32>(cam,0xC4)!=1) {
        ((PickFn)pickOriginal)(view,0,screen,start,end);return;
    }
    U32 *vt=field<U32*>(view,0);
    int width=((IntFn)vt[0x3C/4])(view,0),height=((IntFn)vt[0x44/4])(view,0);
    float nx=2.0f*(screen->x-field<int>(view,0x20))/width-1;
    float ny=1-2.0f*(screen->y-field<int>(view,0x24))/height;
    V2 lo=field<V2>(cam,0xD8),hi=field<V2>(cam,0xE0);
    float x=lo.x+(nx+1)*.5f*(hi.x-lo.x),y=lo.y+(ny+1)*.5f*(hi.y-lo.y);
    Matrix &m=field<Matrix>(cam,0x18);
    float nearZ=field<float>(cam,0xEC),farZ=field<float>(cam,0xF0);
    float *a=&start->x,*b=&end->x;
    for(int i=0;i<3;i++) {
        a[i]=m.m[i][3]+m.m[i][0]*x+m.m[i][1]*y-m.m[i][2]*nearZ;
        b[i]=m.m[i][3]+m.m[i][0]*x+m.m[i][1]*y-m.m[i][2]*farZ;
    }
    bfxState.pickCalls++;
}
extern "C" __declspec(dllexport) void bfxProbe() {
    if(!activeView||!inMatch()) return;
    void *cam=field<void*>(activeView,0x104);
    U32 *vt=field<U32*>(activeView,0);
    int width=((IntFn)vt[0x3C/4])(activeView,0),height=((IntFn)vt[0x44/4])(activeView,0);
    float maxError=0,parallel=0;
    V3 previous={0,0,0};
    for(int i=0;i<3;i++) {
        I2 pixel={width*(i+1)/4,height*(i+1)/4};
        V3 start,end,point,projected;
        pickHook(activeView,0,&pixel,&start,&end);
        float t=-start.z/(end.z-start.z);
        point.x=start.x+(end.x-start.x)*t;
        point.y=start.y+(end.y-start.y)*t;point.z=0;
        address<ProjectFn>(0x135390)(cam,0,&projected,&point);
        float px=(projected.x+1)*width*.5f,py=(1-projected.y)*height*.5f;
        float error=(float)sqrt((px-pixel.x)*(px-pixel.x)+(py-pixel.y)*(py-pixel.y));
        if(error>maxError) maxError=error;
        V3 direction={end.x-start.x,end.y-start.y,end.z-start.z};
        if(i) {
            float difference=(float)(fabs(direction.x-previous.x)+fabs(direction.y-previous.y)+fabs(direction.z-previous.z));
            if(difference>parallel) parallel=difference;
        }
        previous=direction;
    }
    bfxState.pickPixelError=maxError;bfxState.parallelRayError=parallel;
    bfxState.probeCalls++;
}
static void tri(float ax,float ay,float bx,float by,float cx,float cy,U32 color) {
    if(vertexCount+3>65532) return;
    Vertex v[3]={{ax,ay,0,1,color},{bx,by,0,1,color},{cx,cy,0,1,color}};
    memcpy(vertices+vertexCount,v,sizeof(v));vertexCount+=3;
}
static void square(float x,float y,float r,U32 color) {
    tri(x-r,y-r,x+r,y-r,x+r,y+r,color);tri(x-r,y-r,x+r,y+r,x-r,y+r,color);
}
static void diamond(float x,float y,float r,U32 color) {
    tri(x,y-r,x+r,y,x,y+r,color);tri(x,y-r,x,y+r,x-r,y,color);
}
static U32 alpha(U32 color,float a) { return (color&0xffffff)|((U32)(255*a)<<24); }
#include "symbols.inc"
static bool symbolSelected(void *object) {
    // BFME selects the horde drawable; its individual soldiers are contained
    // objects. Follow the native containment chain so the whole battalion lights.
    for(int depth=0;object && depth<8;depth++) {
        void *drawable=field<void*>(object,0x84);
        if(drawable && field<U8>(drawable,0x43C)) return true;
        void *parent=field<void*>(object,0x274);
        if(parent==object) break;
        object=parent;
    }
    return false;
}
typedef HRESULT (__stdcall *Com2)(void*,U32,U32);
typedef HRESULT (__stdcall *ComPointer)(void*,void*);
typedef HRESULT (__stdcall *ComStage)(void*,U32,U32,U32);
static void renderSymbols() {
    bfxState.icons=bfxState.buildings=bfxState.units=bfxState.hiddenSkipped=0;
    bfxSymbols.selectedIcons=bfxSymbols.enemyIcons=0;
    memset(bfxSymbolTypes.current,0,sizeof(bfxSymbolTypes.current));
    float fade=smooth((renderHeight-1400.0f)/600.0f);
    if(!activeView || !inMatch() || activeView!=field<void*>(base,0x9FEA3C) || fade<=0 || bfxState.faults) return;
    void *cam=field<void*>(activeView,0x104);
    void *device=field<void*>(base,0x9EDA34);
    void *players=field<void*>(base,0x9FEEE8);
    void *local=players?field<void*>(players,0x10):0;
    if(!device||!cam||!local) return;
    U32 *vt=field<U32*>(device,0);
    Viewport viewport;
    if(FAILED(((ComPointer)vt[48])(device,&viewport))) return;
    int localIndex=field<int>(local,0x54);
    if(localIndex<0||localIndex>=20) return;
    void *logic=field<void*>(base,0x9FE78C);
    void *obj=field<void*>(logic,0xAC);
    U32 logicFrame=field<U32>(logic,0x40);
    bool trackedSymbol=false;
    vertexCount=0;
    for(int count=0;obj&&count<20000;obj=field<void*>(obj,0x8C),count++) {
        void *tmpl=field<void*>(obj,4),*drawable=field<void*>(obj,0x84);
        if(!tmpl||!drawable||(field<U8>(obj,0x438)&1)) continue;
        void *owner=address<OwnerFn>(0x28AFA9)(obj,0);
        if(!owner) continue;
        if(!address<SelectableFn>(0x28D7FD)(obj,0)) continue;
        // Exactly the three early-out flags in BFME2 Drawable::draw. This also
        // excludes stealth: shroud status alone is insufficient for that.
        if(field<U8>(drawable,0x43D)||field<U8>(drawable,0x43E)||field<U8>(drawable,0x440)) {
            bfxState.hiddenSkipped++;continue;
        }
        if(owner!=local) {
            int shroud=address<ShroudFn>(0x28D2A2)(obj,0,localIndex);
            if(shroud!=1&&shroud!=2) {bfxState.hiddenSkipped++;continue;}
        }
        // Drawable::getTransform is the same cached, client-frame interpolation
        // used by Drawable::draw. Object +0x38 only advances on simulation ticks.
        // Reuse native interpolation instead of introducing an extra smoothing lag.
        const Matrix *transform=address<DrawableTransformFn>(0x27628E)(drawable,0);
        V3 position={transform->m[0][3],transform->m[1][3],transform->m[2][3]},projected;
        if(!_finite(position.x)||!_finite(position.y)||!_finite(position.z)) continue;
        V3 simulation=field<V3>(obj,0x38);
        bool interpolated=fabs(position.x-simulation.x)+fabs(position.y-simulation.y)>.001f;
        bfxSymbols.samples++;
        if(interpolated) bfxSymbols.interpolatedPositions++;
        U32 id=field<U32>(obj,0x74);
        if(!symbolObject && interpolated) {
            symbolObject=id;symbolPosition=position;symbolLogicFrame=logicFrame;
        }
        if(symbolObject && id==symbolObject) {
            trackedSymbol=true;
            if(fabs(position.x-symbolPosition.x)+fabs(position.y-symbolPosition.y)>.001f) {
                if(logicFrame==symbolLogicFrame) bfxSymbols.betweenLogicMoves++;
                else bfxSymbols.logicMoves++;
            }
            symbolPosition=position;symbolLogicFrame=logicFrame;
        }
        int projectedStatus=address<ProjectFn>(0x135390)(cam,0,&projected,&position);
        if(projectedStatus!=0) continue;
        float x=viewport.x+(projected.x+1)*viewport.width*.5f;
        float y=viewport.y+(1-projected.y)*viewport.height*.5f;
        if(x<12||y<12||x>viewport.width-12||y>viewport.height-15) continue;
        // Native palantir/control bar remains on top conceptually.
        // BFME scales its palantir/control bar with the viewport dimensions.
        if(y>viewport.y+viewport.height*(1-260.0f/768) &&
           x<viewport.x+viewport.width*(400.0f/1024)) continue;
        SymbolKind kind=symbolKind(obj,tmpl);
        bool selected=symbolSelected(obj);
        bool enemy=owner!=local && address<RelationshipFn>(0x2AD0C6)(local,0,field<void*>(obj,0x304))==0;
        U32 color=alpha(enemy?0xF04444:address<ColorFn>(0x28B026)(obj,0),fade);
        U32 white=alpha(0xF3E5BC,fade),dark=alpha(0x071018,fade);
        U32 border=alpha(selected?0xFFE45C:0xD0C6AD,fade);
        if(selected)bfxSymbols.selectedIcons++;
        if(enemy)bfxSymbols.enemyIcons++;
        tacticalSymbol(kind,x,y,selected,color,border,white,dark);
        if(kind==BUILDING)bfxState.buildings++;else bfxState.units++;
        bfxState.icons++;
    }
    if(!trackedSymbol) symbolObject=0;
    for(int kindIndex=0;kindIndex<SYMBOL_KINDS;kindIndex++)
        if(bfxSymbolTypes.current[kindIndex]>bfxSymbolTypes.peak[kindIndex])
            bfxSymbolTypes.peak[kindIndex]=bfxSymbolTypes.current[kindIndex];
    if(bfxSymbols.selectedIcons>bfxSymbols.peakSelectedIcons)bfxSymbols.peakSelectedIcons=bfxSymbols.selectedIcons;
    if(bfxSymbols.enemyIcons>bfxSymbols.peakEnemyIcons)bfxSymbols.peakEnemyIcons=bfxSymbols.enemyIcons;
    if(!vertexCount) return;
    void *state=0;
    typedef HRESULT (__stdcall *MakeState)(void*,U32,void**);
    if(FAILED(((MakeState)vt[59])(device,1,&state))||!state) return;
    ((ComPointer)vt[92])(device,0);((ComPointer)vt[107])(device,0);
    typedef HRESULT (__stdcall *OneWord)(void*,U32);
    ((OneWord)vt[89])(device,0x44);
    typedef HRESULT (__stdcall *Texture)(void*,U32,void*);
    ((Texture)vt[65])(device,0,0);
    const U32 states[][2]={{7,0},{14,0},{137,0},{27,1},{19,5},{20,6},{22,1},{15,0},{28,0},{174,0},{52,0},{168,15},{152,0}};
    for(int i=0;i<sizeof(states)/sizeof(states[0]);i++) ((Com2)vt[57])(device,states[i][0],states[i][1]);
    ((ComStage)vt[67])(device,0,1,2);((ComStage)vt[67])(device,0,2,0);
    ((ComStage)vt[67])(device,0,4,2);((ComStage)vt[67])(device,0,5,0);
    ((ComStage)vt[67])(device,1,1,1);
    typedef HRESULT (__stdcall *Draw)(void*,U32,U32,const void*,U32);
    HRESULT result=((Draw)vt[83])(device,4,vertexCount/3,vertices,sizeof(Vertex));
    if(FAILED(result)) bfxState.lastError=result;
    U32 *svt=field<U32*>(state,0);
    typedef HRESULT (__stdcall *NoArgs)(void*);
    ((NoArgs)svt[5])(state);((NoArgs)svt[2])(state);
    bfxState.drawCalls++;
}
static void __cdecl endHook(bool flip) {
    __try {traceCamera(activeView,3);renderSymbols();}
    __except(EXCEPTION_EXECUTE_HANDLER) {bfxState.faults++;bfxState.lastError=GetExceptionCode();}
    ((EndFn)endOriginal)(flip);
}
static void *hook(U32 rva,void *replacement,const U8 *expected,int length) {
    U8 *src=base+rva;
    if(memcmp(src,expected,length)) return 0;
    U8 *stub=(U8*)VirtualAlloc(0,length+5,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);
    if(!stub) return 0;
    memcpy(stub,src,length);stub[length]=0xe9;
    *(U32*)(stub+length+1)=(U32)(src+length)-(U32)(stub+length+5);
    DWORD old;
    if(!VirtualProtect(src,length,PAGE_EXECUTE_READWRITE,&old)) return 0;
    src[0]=0xe9;*(U32*)(src+1)=(U32)replacement-(U32)(src+5);
    for(int i=5;i<length;i++) src[i]=0x90;
    VirtualProtect(src,length,old,&old);FlushInstructionCache(GetCurrentProcess(),src,length);
    return stub;
}
static void undoHook(U32 rva,void *trampoline,int length) {
    if(!trampoline) return;
    DWORD old;
    if(VirtualProtect(base+rva,length,PAGE_EXECUTE_READWRITE,&old)) {
        memcpy(base+rva,trampoline,length);
        VirtualProtect(base+rva,length,old,&old);
        FlushInstructionCache(GetCurrentProcess(),base+rva,length);
    }
}
#include "battle.inc"
#include "showcase.inc"

BOOL WINAPI DllMain(HINSTANCE instance,DWORD reason,LPVOID) {
    if(reason!=DLL_PROCESS_ATTACH) return TRUE;
    DisableThreadLibraryCalls(instance);
    base=(U8*)GetModuleHandleA(0);
    QueryPerformanceFrequency(&timerFrequency);
    // Validate all complete instruction spans before touching any.
    const U8 cameraBytes[]={0xb8,0x15,0xfd,0xb5,0x00};
    const U8 pickBytes[]={0x55,0x8b,0xec,0x83,0xec,0x14};
    const U8 endBytes[]={0x64,0xa1,0,0,0,0};
    const U8 updateBytes[]={0x81,0xc1,0xb4,0,0,0};
    const U8 healthBytes[]={0x8d,0x44,0x24,0x08,0x50};
    if(base!=(U8*)0x400000||memcmp(base+0x8BE6B,cameraBytes,5)||
       memcmp(base+0x89658,pickBytes,6)||memcmp(base+0x122BE0,endBytes,6)||
       memcmp(base+0x85B36,updateBytes,6)||memcmp(base+0x239FCC,healthBytes,5)) return FALSE;
    cameraOriginal=hook(0x8BE6B,cameraHook,cameraBytes,5);
    pickOriginal=hook(0x89658,pickHook,pickBytes,6);
    endOriginal=hook(0x122BE0,endHook,endBytes,6);
    updateOriginal=hook(0x85B36,updateHook,updateBytes,6);
    healthOriginal=hook(0x239FCC,healthHook,healthBytes,5);
    if(!cameraOriginal||!pickOriginal||!endOriginal||!updateOriginal||!healthOriginal) {
        undoHook(0x8BE6B,cameraOriginal,5);
        undoHook(0x89658,pickOriginal,6);
        undoHook(0x122BE0,endOriginal,6);
        undoHook(0x85B36,updateOriginal,6);
        undoHook(0x239FCC,healthOriginal,5);
        return FALSE;
    }
    bfxState.installed=1;
    return TRUE;
}
