// Shared native ABI types; retain the 32-bit layout.
typedef unsigned char U8;
typedef unsigned int U32;
struct V3 { float x,y,z; };
struct V2 { float x,y; };
struct I2 { int x,y; };
struct Matrix { float m[3][4]; };
struct Vertex { float x,y,z,rhw; U32 color; };
struct Viewport { U32 x,y,width,height; float minZ,maxZ; };
