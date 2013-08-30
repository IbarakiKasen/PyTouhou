from pytouhou.lib.opengl cimport GLuint

cdef struct Vertex:
    float x, y, z
    float u, v
    unsigned char r, g, b, a


cdef class BackgroundRenderer:
    cdef GLuint texture
    cdef unsigned short blendfunc, nb_vertices
    cdef Vertex *vertex_buffer
    cdef unsigned int use_fixed_pipeline, vbo

    cpdef render_background(self)
    cpdef prerender(self, background)