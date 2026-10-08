// Opt-in render-target readback for map QA. No desktop/window capture required.
struct CaptureState { U32 request,status,width,height,pitch,pixels; };
extern "C" __declspec(dllexport) CaptureState bfxCapture={0};
static U32 captureCapacity;
static void captureFrame() {
    if(!bfxCapture.request)return;
    bfxCapture.request=0;bfxCapture.status=0x80004005;
    void *device=field<void*>(base,0x9EDA34);if(!device)return;
    U32 *vt=field<U32*>(device,0);void *target=0,*copy=0;
    typedef HRESULT (__stdcall *GetTarget)(void*,U32,void**);
    typedef HRESULT (__stdcall *CreateSurface)(void*,U32,U32,U32,U32,void**,void*);
    typedef HRESULT (__stdcall *CopySurface)(void*,void*,void*);
    typedef HRESULT (__stdcall *DescFn)(void*,void*);
    typedef HRESULT (__stdcall *LockFn)(void*,void*,void*,U32);
    typedef HRESULT (__stdcall *SimpleFn)(void*);
    U32 desc[8]={0};struct Lock { int pitch;void *bits; } locked;
    HRESULT result=((GetTarget)vt[38])(device,0,&target);
    if(SUCCEEDED(result)&&target) {
        U32 *tv=field<U32*>(target,0);
        result=((DescFn)tv[12])(target,desc);
        if(SUCCEEDED(result)&&(desc[0]==21||desc[0]==22)&&desc[6]&&desc[7]&&desc[6]<=4096&&desc[7]<=4096) {
            result=((CreateSurface)vt[36])(device,desc[6],desc[7],desc[0],2,&copy,0);
            if(SUCCEEDED(result)&&copy) {
                result=((CopySurface)vt[32])(device,target,copy);
                U32 *cv=field<U32*>(copy,0);
                if(SUCCEEDED(result))result=((LockFn)cv[13])(copy,&locked,0,0x10);
                if(SUCCEEDED(result)) {
                    U32 size=desc[6]*desc[7]*4;
                    if(size>captureCapacity) {
                        if(bfxCapture.pixels)VirtualFree((void*)bfxCapture.pixels,0,MEM_RELEASE);
                        bfxCapture.pixels=(U32)VirtualAlloc(0,size,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);
                        captureCapacity=bfxCapture.pixels?size:0;
                    }
                    if(bfxCapture.pixels) {
                        for(U32 y=0;y<desc[7];y++)memcpy((U8*)bfxCapture.pixels+y*desc[6]*4,(U8*)locked.bits+y*locked.pitch,desc[6]*4);
                        bfxCapture.width=desc[6];bfxCapture.height=desc[7];bfxCapture.pitch=desc[6]*4;
                    } else result=0x8007000E;
                    ((SimpleFn)cv[14])(copy);
                }
                ((SimpleFn)cv[2])(copy);
            }
        } else if(SUCCEEDED(result))result=0x80004001;
        ((SimpleFn)tv[2])(target);
    }
    bfxCapture.status=result;
}
