from evaluate_tracking import evaluate

def test_identity_switch_counts_and_false_positive():
    gt={1:[('a','drone',[0,0,10,10])],2:[('a','drone',[0,0,10,10])],3:[('a','drone',[0,0,10,10])]}
    pred={1:[('1','drone',[0,0,10,10])],2:[('2','drone',[0,0,10,10]),('3','bird',[30,30,40,40])]}
    r=evaluate(gt,pred)
    assert r['id_switches']==1
    assert r['matched_observations']==2 and r['misses']==1 and r['false_positives']==1
    assert r['recall']==2/3 and r['precision']==2/3
    assert r['mean_track_coverage']==2/3
