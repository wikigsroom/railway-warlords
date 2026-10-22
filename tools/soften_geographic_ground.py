"""Derive numeric material-mixing weights; never synthesize raster artwork.

The source ecological IDs remain unmodified. A 0.25 degree illustrative
transition removes one-node stair steps, without changing any source boundary,
rule cell, historical land-use assertion or original generated texture.
"""
from pathlib import Path
import base64
import gzip
import hashlib
import json
import sys

P=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(P.parents[1]/'.toolchain/python-libs'))
import numpy as np
from scipy.ndimage import gaussian_filter


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    directory=P/'reports/geographic_ground_v0237'
    assert (directory/'source_audit01.json').exists(), 'Complete raw polygon audit before deriving weights'
    source=P/'presentation/data/asia_ground_regions.json'
    data=json.loads(source.read_bytes())
    assert 'weights_data_base64' not in data
    original_sha=sha(source)
    assert json.loads((directory/'source_audit01.json').read_bytes())['source_data_sha256']==original_sha
    archive=directory/'iterations01'
    assert (archive/'asia_ground_regions.json').read_bytes()==source.read_bytes()
    material=np.frombuffer(gzip.decompress(base64.b64decode(data['data_base64'])),dtype='u1').reshape(901,1601)
    weights=np.stack([gaussian_filter((material==index+1).astype(np.float32),sigma=2.5,mode='constant',truncate=3.)[::2,::2]
                      for index in range(len(data['family_names']))])
    total=weights.sum(axis=0)
    weights/=np.maximum(total,1e-8)
    packed=np.rint(weights*255).astype('u1')
    raw=packed.tobytes()
    data.update(classification_source_json_sha256=original_sha,weights_dimensions=[801,451],weights_layers=len(data['family_names']),
        weights_encoding='gzip_base64_uint8_per_family_layer_row_major_linear_numeric_weights',
        weights_uncompressed_bytes=len(raw),weights_payload_sha256=hashlib.sha256(raw).hexdigest(),
        weights_data_base64=base64.b64encode(gzip.compress(raw,mtime=0)).decode('ascii'),
        transition_sigma_degrees=.25,transition_kernel_radius_degrees=.75,
        transition_weights_are_illustration_not_measured_ecotone=True,classification_nodes_unchanged=True,
        weight_texture_step_degrees=.2,source_polygon_gaps_still_use_unsmoothed_classification_mask=True)
    source.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    report=dict(passed=True,source_data_sha256=sha(source),classification_source_json_sha256=original_sha,
        controller_sha256=sha(Path(__file__)),weights_dimensions=[801,451],layers=len(data['family_names']),
        gpu_lookup_bytes=len(raw),weights_payload_sha256=data['weights_payload_sha256'],
        maximum_quantized_sum_error=float(np.max(np.abs(packed.sum(axis=0)[total>1e-8]/255-1))),
        source_classification_payload_unchanged=True,actual_historical_ecotone_width_claimed=False,
        new_raster_art=False,source_images_modified=False)
    (directory/'weight_derivation01.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
