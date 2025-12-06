try:
    from jnius import autoclass
    Camera = autoclass('android.hardware.thermal-camera')
except Exception:
    Camera = None

HEATMAP_FS = """
#ifdef GL_ES
    precision mediump float;
#endif
varying vec2 tex_coord0;
uniform sampler2D texture0;
void main() {
    vec4 c = texture2D(texture0, tex_coord0);
    float g = (c.r + c.g + c.b) / 3.0;
    float t = clamp(g, 0.0, 1.0);
    vec3 heat = vec3(0.0);
    if (t < 0.25) {
        heat = vec3(0.0, 4.0*t, 1.0);
    } else if (t < 0.5) {
        heat = vec3(0.0, 1.0, 1.0 - 4.0*(t-0.25));
    } else if (t < 0.75) {
        heat = vec3(4.0*(t-0.5), 1.0, 0.0);
    } else {
        heat = vec3(1.0, 1.0 - 4.0*(t-0.75), 0.0);
    }
    gl_FragColor = vec4(heat, 1.0);
}
"""

def has_ir() -> bool:
    return Camera is not None

def get_heatmap_shader() -> str:
    return HEATMAP_FS