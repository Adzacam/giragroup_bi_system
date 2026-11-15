import pytest
from scripts.evaluar_f0_gold import match, metrics, spans_iob2, sha, validate_provenance


def test_relaxed_reserves_each_prediction_once():
    gold=[('MODULO',0,2),('MODULO',2,4)]
    pred=[('MODULO',0,4)]
    assert len(match(gold,pred,True))==1
    assert metrics(1,0,1)['recall']==0.5


def test_matching_finds_maximum_cardinality_instead_of_greedy():
    gold=[('MODULO',0,4),('MODULO',0,2)]
    pred=[('MODULO',0,2),('MODULO',2,4)]
    assert match(gold,pred,True)==[(0,1),(1,0)]


def test_strict_rejects_partial_overlap_and_wrong_type():
    assert match([('MODULO',0,4)],[('MODULO',0,2)])==[]
    assert match([('MODULO',0,4)],[('PROGRAMA',0,4)],True)==[]
    assert match([('MODULO',0,4)],[('MODULO',0,4)])==[(0,0)]


def test_strict_iob2_orphan_i_does_not_create_entity():
    assert spans_iob2(['I-MODULO','B-PROGRAMA','I-PROGRAMA','I-MODULO','B-MODULO'])==[('PROGRAMA',1,3),('MODULO',4,5)]


def test_empty_counts_are_undefined_not_zero_rate():
    result=metrics(0,0,0)
    assert result['precision'] is result['recall'] is result['f1'] is None


def test_recovery_rejects_incomplete_provenance(tmp_path):
    with pytest.raises(ValueError,match='not completed'):
        validate_provenance({'status':'inference_pending'},tmp_path/'pred.json',tmp_path)


@pytest.mark.parametrize('altered',['gold','prediction','model','evaluator'])
def test_recovery_rejects_changed_gold_prediction_model_or_evaluator(tmp_path,altered):
    paths={'gold':tmp_path/'data/test_gold_real.jsonl',
           'prediction':tmp_path/'pred.json',
           'model':tmp_path/'pipeline/semantic/beto_local/model.safetensors',
           'evaluator':tmp_path/'scripts/ablacion_beto.py'}
    for path in paths.values():
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(b'original bytes')
    metadata={'status':'complete','gold_sha256':sha(paths['gold']),
              'predictions_sha256':sha(paths['prediction']),
              'evaluator_sha256':sha(paths['evaluator']),
              'model_files':{'model.safetensors':{'sha256':sha(paths['model'])}}}
    validate_provenance(metadata,paths['prediction'],tmp_path)
    paths[altered].write_bytes(b'changed')
    with pytest.raises(ValueError,match='hash mismatch'):
        validate_provenance(metadata,paths['prediction'],tmp_path)
