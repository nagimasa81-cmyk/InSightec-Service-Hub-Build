import numpy as np

from core.auto_correct import _bright_blob_mask


def _gaussian(shape, cy, cx, sy, sx, amplitude):
    y, x = np.indices(shape)
    return amplitude * np.exp(-0.5 * (((y-cy)/sy)**2 + ((x-cx)/sx)**2))


def test_detects_four_soft_edge_blobs_and_excludes_dc():
    shape=(256,256)
    rng=np.random.default_rng(114)
    mag=np.abs(rng.normal(0.0,0.55,shape)) + 1.0
    # Strong normal DC energy must not become part of the artifact mask.
    mag += _gaussian(shape,127.5,127.5,11,11,22.0)
    expected=[(72,0),(184,0),(72,255),(184,255)]
    for cy,cx in expected:
        mag += _gaussian(shape,cy,cx,8.5,13.0,10.0)
    mask=_bright_blob_mask(mag.astype(np.complex128),0.78,0.58)
    assert not mask[128-5:128+6,128-5:128+6].any()
    for cy,cx in expected:
        x0=0 if cx==0 else 244
        x1=12 if cx==0 else 256
        assert int(mask[max(0,cy-12):min(256,cy+13),x0:x1].sum()) >= 8


def test_nonwrapping_growth_does_not_bridge_opposite_edges():
    shape=(128,128)
    rng=np.random.default_rng(15)
    mag=np.abs(rng.normal(0.0,0.35,shape))+1.0
    mag += _gaussian(shape,38,0,6,8,8.0)
    mask=_bright_blob_mask(mag.astype(np.complex128),0.8,0.55)
    assert mask[25:52,:10].any()
    # The connected region starting at the left blob must not wrap to the
    # opposite side or extend through the FFT centre.
    seed=np.argwhere(mask[25:52,:10])
    assert seed.size
    y0,x0=seed[0]; y0+=25
    seen={(int(y0),int(x0))}; stack=[(int(y0),int(x0))]
    while stack:
        y,x=stack.pop()
        for ny in range(max(0,y-1),min(shape[0],y+2)):
            for nx in range(max(0,x-1),min(shape[1],x+2)):
                if mask[ny,nx] and (ny,nx) not in seen:
                    seen.add((ny,nx)); stack.append((ny,nx))
    assert max(x for _,x in seen) < 32
