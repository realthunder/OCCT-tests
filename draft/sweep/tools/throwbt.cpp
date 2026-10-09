#include <cxxabi.h>
#include <dlfcn.h>
#include <execinfo.h>
#include <cstdio>
#include <typeinfo>
extern "C" void __cxa_throw(void*, std::type_info*, void (*)(void*));
static void my_throw(void* obj, std::type_info* t, void (*d)(void*))
{
    void* bt[40];
    int n = backtrace(bt, 40);
    fprintf(stderr, "THROW %s\n", t ? t->name() : "?");
    for (int i = 1; i < n && i < 14; ++i) {
        Dl_info info;
        if (dladdr(bt[i], &info) && info.dli_fname) {
            fprintf(stderr, "  #%d %s +0x%lx %s\n", i, info.dli_fname,
                    (unsigned long)((char*)bt[i] - (char*)info.dli_fbase),
                    info.dli_sname ? info.dli_sname : "?");
        }
    }
    __cxa_throw(obj, t, d);
}
struct interpose { const void* repl; const void* orig; };
__attribute__((used)) static const interpose interposers[] __attribute__((section("__DATA,__interpose"))) = {
    {(const void*)&my_throw, (const void*)&__cxa_throw}};
