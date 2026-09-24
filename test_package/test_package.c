#include <freerdp/client.h>
#include <freerdp/codec/h264.h>
#include <freerdp/listener.h>
#include <winpr/ssl.h>

int main(void)
{
	freerdp_listener* listener = freerdp_listener_new();
	H264_CONTEXT* h264 = h264_context_new(FALSE);
	int const ok = listener && h264 && winpr_InitializeSSL(WINPR_SSL_INIT_DEFAULT);
	h264_context_free(h264);
	freerdp_listener_free(listener);
	return ok ? 0 : 1;
}
