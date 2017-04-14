#include <stdlib.h>

__declspec(dllexport) void __stdcall Foo(unsigned char** ppMem, int* pSize)
{
    char i;
    *pSize = 4;
    *ppMem = malloc(*pSize);
    for(i = 0; i < *pSize; i++)
        (*ppMem)[i] = i;
}
