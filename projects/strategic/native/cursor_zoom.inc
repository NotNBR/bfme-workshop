// Keep the terrain point under a wheel event fixed through native zoom easing
// and the perspective/orthographic transition. Scripted camera moves opt out.
struct CursorZoomState {
    U32 active,events,corrections,rejected;
    I2 pixel;
    V3 anchor;
    float pixelError,maxPixelError;
};
extern "C" __declspec(dllexport) CursorZoomState bfxCursorZoom={0};
static LARGE_INTEGER zoomStarted;
static LARGE_INTEGER zoomStableSince;
static float zoomBearing;
static float zoomLastHeight,zoomLastBlend;

static bool directedCamera() {
    return bfxPhoto.enabled || bfxMovie.enabled || (bfxShowcase.enabled&&!bfxShowcase.finished);
}
extern "C" __declspec(dllexport) void __cdecl bfxZoomBegin(int x,int y) {
    bfxCursorZoom.active=0;
    void *view=field<void*>(base,0x9FEA3C);
    if(!view||!inMatch()||directedCamera()||!field<void*>(view,0x104)) return;
    U32 *vt=field<U32*>(view,0);
    int width=((IntFn)vt[0x3C/4])(view,0),height=((IntFn)vt[0x44/4])(view,0);
    int px=x-field<int>(view,0x20),py=y-field<int>(view,0x24);
    // The palantir and command panel are not terrain. Keep native HUD behavior.
    if(width<=0||height<=0||px<0||py<0||px>=width||py>=height||
       (py>height*(1-260.0f/768)&&px<width*(400.0f/1024))) {
        bfxCursorZoom.rejected++;return;
    }
    I2 pixel={x,y};V3 point={FLT_MAX,FLT_MAX,FLT_MAX};
    typedef void (__fastcall *TerrainPickFn)(void*,void*,const I2*,V3*,bool);
    ((TerrainPickFn)vt[0x168/4])(view,0,&pixel,&point,false);
    if(!_finite(point.x)||!_finite(point.y)||!_finite(point.z)||
       fabs(point.x)>1000000||fabs(point.y)>1000000||fabs(point.z)>100000) {
        bfxCursorZoom.rejected++;return;
    }
    bfxCursorZoom.pixel=pixel;bfxCursorZoom.anchor=point;
    bfxCursorZoom.active=1;bfxCursorZoom.events++;
    bfxCursorZoom.pixelError=bfxCursorZoom.maxPixelError=0;
    zoomBearing=field<float>(view,0x28);
    QueryPerformanceCounter(&zoomStarted);
    zoomStableSince=zoomStarted;zoomLastHeight=renderHeight;zoomLastBlend=tilt;
}
typedef void (__fastcall *MouseEventFn)(void*,void*,UINT,WPARAM,LPARAM,DWORD);
static void __fastcall mouseHook(void *mouse,void*,UINT message,WPARAM w,LPARAM l,DWORD time) {
    // Only arm events accepted into the native ring. Preserve its input handling.
    U32 next=field<U32>(mouse,0x6010);
    if(message==WM_MOUSEWHEEL && (short)HIWORD(w)!=0 && next<256 &&
       field<U32>(mouse,0x5010+16*next)==0) {
        HWND window=field<HWND>(base,0x9DE024);
        POINT point={(short)LOWORD(l),(short)HIWORD(l)};
        if(window && GetForegroundWindow()==window && ScreenToClient(window,&point))
            bfxZoomBegin(point.x,point.y);
    }
    ((MouseEventFn)mouseOriginal)(mouse,0,message,w,l,time);
}
static void finishCursorZoom(void *view,const V3 &previousFocus) {
    if(!bfxCursorZoom.active) return;
    if(!inMatch()||directedCamera()||fabs(field<float>(view,0x28)-zoomBearing)>.001f) {
        bfxCursorZoom.active=0;return;
    }
    void *cam=field<void*>(view,0x104);
    if(!cam) {bfxCursorZoom.active=0;return;}
    V3 focus=field<V3>(view,0x0C);
    // Preserve explicit scrolling/panning instead of fighting it.
    bfxCursorZoom.anchor.x+=focus.x-previousFocus.x;
    bfxCursorZoom.anchor.y+=focus.y-previousFocus.y;
    V3 start,end;
    pickHook(view,0,&bfxCursorZoom.pixel,&start,&end);
    float dz=end.z-start.z;
    if(!_finite(dz)||fabs(dz)<.001f) {bfxCursorZoom.active=0;return;}
    float t=(bfxCursorZoom.anchor.z-start.z)/dz;
    float dx=bfxCursorZoom.anchor.x-(start.x+(end.x-start.x)*t);
    float dy=bfxCursorZoom.anchor.y-(start.y+(end.y-start.y)*t);
    if(!_finite(dx)||!_finite(dy)||t<0||t>1||fabs(dx)>50000||fabs(dy)>50000) {
        bfxCursorZoom.active=0;bfxCursorZoom.rejected++;return;
    }
    // Translate both the native focus and the already-built render transform.
    // Do not rebuild here: that would advance native height easing twice.
    field<float>(view,0x0C)+=dx;field<float>(view,0x10)+=dy;
    Matrix mat=field<Matrix>(cam,0x18);
    mat.m[0][3]+=dx;mat.m[1][3]+=dy;
    address<TransformFn>(0x13B790)(cam,0,&mat);
    field<U8>(cam,0xFC)=0;
    bfxCursorZoom.corrections++;
    V3 projected;
    address<ProjectFn>(0x135390)(cam,0,&projected,&bfxCursorZoom.anchor);
    U32 *vt=field<U32*>(view,0);
    int width=((IntFn)vt[0x3C/4])(view,0),height=((IntFn)vt[0x44/4])(view,0);
    float ex=field<int>(view,0x20)+(projected.x+1)*width*.5f-bfxCursorZoom.pixel.x;
    float ey=field<int>(view,0x24)+(1-projected.y)*height*.5f-bfxCursorZoom.pixel.y;
    bfxCursorZoom.pixelError=(float)sqrt(ex*ex+ey*ey);
    if(bfxCursorZoom.pixelError>bfxCursorZoom.maxPixelError)
        bfxCursorZoom.maxPixelError=bfxCursorZoom.pixelError;
    LARGE_INTEGER now;QueryPerformanceCounter(&now);
    float seconds=(float)((double)(now.QuadPart-zoomStarted.QuadPart)/timerFrequency.QuadPart);
    // Retail easing stops a few units short of the requested height. Detect
    // a stable rendered camera instead of waiting for an exact target match.
    if(fabs(renderHeight-zoomLastHeight)>.01f || fabs(tilt-zoomLastBlend)>.00001f || fabs(tiltVelocity)>.001f)
        zoomStableSince=now;
    zoomLastHeight=renderHeight;zoomLastBlend=tilt;
    float stable=(float)((double)(now.QuadPart-zoomStableSince.QuadPart)/timerFrequency.QuadPart);
    if(seconds>.3f && stable>.25f)
        bfxCursorZoom.active=0;
}
