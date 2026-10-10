// Native render-target video: only game pixels, recorded to a temporary raw file.
struct MovieShot { float x,y,span,elevation,panX,panY,endSpan,endElevation; U32 frames,strategic; };
struct MovieState { U32 enabled,frames,error,complete,limit,exitCode,shots; char command[2048]; U32 strategicFrames,peakIcons; };
extern "C" __declspec(dllexport) MovieState bfxMovie={0};
extern "C" __declspec(dllexport) MovieShot bfxMovieShots[12]={0};
static HANDLE moviePipe=0;
static void movieCamera(void *view) {
    if(!bfxMovie.enabled||bfxMovie.complete||bfxMovie.error||!bfxMovie.shots){movieSymbolFade=-1;return;}
    U32 f=bfxMovie.frames;U32 shot=0;
    while(shot+1<bfxMovie.shots&&f>=bfxMovieShots[shot].frames){f-=bfxMovieShots[shot].frames;shot++;}
    MovieShot &s=bfxMovieShots[shot];float u=(float)f/(float)(s.frames>1?s.frames-1:1);
    // Zero acceleration at each endpoint; constant perceived scale through a
    // logarithmic zoom avoids rushing through the final close-up.
    float t=u*u*u*(u*(u*6-15)+10);
    float span=s.span*(float)pow(s.endSpan/s.span,t);
    bfxPhoto.enabled=1;bfxPhoto.x=s.x+s.panX*t;bfxPhoto.y=s.y+s.panY*t;bfxPhoto.z=160;
    bfxPhoto.elevation=s.elevation+(s.endElevation-s.elevation)*t;
    movieSymbolFade=s.strategic?smooth((span-2800)/1800):0;
    // Keep native model LODs near the photographed action. Map tiles use a
    // distant parallel camera, but that distance reduces infantry to silhouettes.
    photoDistance=span*.70f+500;
    typedef void (__fastcall *MoviePositionFn)(void*,void*,const V3*);
    typedef void (__fastcall *MovieHeightFn)(void*,void*,float);
    V3 focus={bfxPhoto.x,bfxPhoto.y,160};
    address<MoviePositionFn>(0x8D55D)(view,0,&focus);
    address<MovieHeightFn>(0x8D2B8)(view,0,photoDistance*(float)sin(bfxPhoto.elevation));
    bfxPhoto.left=-span*.5f;bfxPhoto.right=span*.5f;
    bfxPhoto.top=span*.225f;bfxPhoto.bottom=bfxPhoto.top-span*.75f;
}
static void movieFrame() {
    if(!bfxMovie.enabled||bfxMovie.complete||bfxMovie.error)return;
    if(bfxMovie.frames>=bfxMovie.limit) {
        if(moviePipe){CloseHandle(moviePipe);moviePipe=0;}
        bfxMovie.exitCode=0;bfxMovie.complete=1;
        return;
    }
    if(!moviePipe) {
        moviePipe=CreateFileA(bfxMovie.command,GENERIC_WRITE,FILE_SHARE_READ,0,CREATE_ALWAYS,FILE_FLAG_SEQUENTIAL_SCAN,0);
        if(moviePipe==INVALID_HANDLE_VALUE){moviePipe=0;bfxMovie.error=2;return;}
    }
    bfxCapture.request=1;captureFrame();
    if(movieSymbolFade>.5f&&bfxState.icons) {
        bfxMovie.strategicFrames++;
        if(bfxState.icons>bfxMovie.peakIcons)bfxMovie.peakIcons=bfxState.icons;
    }
    if(bfxCapture.status||bfxCapture.width!=1600||bfxCapture.height!=1200||bfxCapture.pitch!=6400) {
        bfxMovie.error=bfxCapture.status?bfxCapture.status:3;CloseHandle(moviePipe);moviePipe=0;return;
    }
    DWORD bytes=1600*720*4,offset=0;
    while(offset<bytes) {
        DWORD written=0;
        if(!WriteFile(moviePipe,(U8*)bfxCapture.pixels+offset,bytes-offset,&written,0)||!written) {
            bfxMovie.error=4;CloseHandle(moviePipe);moviePipe=0;return;
        }
        offset+=written;
    }
    bfxMovie.frames++;
}
