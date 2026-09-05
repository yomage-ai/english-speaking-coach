"""Synthetic teaching examples: translation coverage, not wording/style snapshots."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from codex_translation import translation_units, assemble_translations, CodexTranslator


class MeaningTests(unittest.TestCase):
    def test_each_english_example_gets_meaning_without_changing_original(self):
        segments = [{'id':'a','role':'assistant','text':'问价格可以说：“How much is this?”；要打包说：“Please wrap it up.”'},
                    {'id':'b','role':'assistant','text':'想问优惠可以说:Can you give me a discount?'}]
        before=deepcopy(segments);units=translation_units(segments)
        self.assertEqual(len(units),3)
        meanings=['这个多少钱？','请帮我包起来。','可以给我打折吗？']
        result=assemble_translations(segments,units,[{'id':u['id'],'chinese':m,'kind':'translation'} for u,m in zip(units,meanings)])
        self.assertIn('这个多少钱',result[0]['chinese']);self.assertIn('包起来',result[0]['chinese'])
        self.assertIn('打折',result[1]['chinese']);self.assertNotIn('How much',result[0]['chinese'])
        self.assertEqual(segments,before)

    def test_previous_echo_with_chinese_wrapper_is_not_completion(self):
        segments=[{'id':'a','role':'assistant','text':'你可以说:Can you give me a discount?'}]
        units=translation_units(segments)
        for wrong in ['Can you give me a discount?', '你可以说：“Can you give me a discount?”']:
            with self.assertRaises(ValueError):
                assemble_translations(segments,units,[{'id':units[0]['id'],'chinese':wrong,'kind':'translation'}])

    def test_ascii_wrappers_survive_and_contractions_stay_together(self):
        for wrapper in [('"','"'), ("'","'"), ('(',')')]:
            text='可以说：'+wrapper[0]+"That's all for today."+wrapper[1]
            segments=[{'id':'a','text':text}];units=translation_units(segments)
            self.assertEqual([u['text'] for u in units],["That's all for today."])
            result=assemble_translations(segments,units,[{'id':units[0]['id'],'chinese':'今天就这些。','kind':'translation'}])
            self.assertEqual(result[0]['chinese'],'可以说：'+wrapper[0]+'今天就这些。'+wrapper[1])

    def test_missing_duplicate_or_wrong_unit_is_rejected(self):
        segments=[{'id':'a','text':'请问“How much is this?”，然后说“Thank you.”'}]
        units=translation_units(segments)
        one={'id':units[0]['id'],'chinese':'多少钱？','kind':'translation'}
        for result in [[one],[one,one],[one,{'id':'wrong','chinese':'谢谢。','kind':'translation'}]]:
            with self.assertRaises(ValueError):assemble_translations(segments,units,result)

    def test_single_word_and_proper_name_are_distinguished(self):
        segments=[{'id':'a','text':'“Discount”是什么意思？'},{'id':'b','text':'商品名是Labubu。'}]
        units=translation_units(segments)
        result=assemble_translations(segments,units,[{'id':units[0]['id'],'chinese':'折扣','kind':'translation'},
                    {'id':units[1]['id'],'chinese':'Labubu','kind':'name'}])
        self.assertIn('折扣',result[0]['chinese']);self.assertIn('Labubu',result[1]['chinese'])

    def test_sentence_cannot_bypass_check_as_a_name(self):
        segments=[{'id':'a','text':'Can you give me a discount?'}];units=translation_units(segments)
        with self.assertRaises(ValueError):
            assemble_translations(segments,units,[{'id':units[0]['id'],'chinese':segments[0]['text'],'kind':'name'}])

    def test_chinese_only_needs_no_model_or_connection(self):
        client=CodexTranslator()
        client.connect=lambda: self.fail('No model connection needed')
        result,latency=client.translate([{'id':'a','role':'user','text':'请帮我包起来。'}])
        self.assertEqual(result,[{'id':'a','chinese':'请帮我包起来。'}]);self.assertEqual(latency,0)

    def test_pure_english_remains_one_unit_and_preserves_numbers(self):
        segments=[{'id':'a','text':"If it's $50 each, I'll buy two."}];units=translation_units(segments)
        self.assertEqual(len(units),1);self.assertEqual(units[0]['text'],segments[0]['text'])
        result=assemble_translations(segments,units,[{'id':units[0]['id'],'chinese':'如果每个50美元，我就买两个。','kind':'translation'}])
        self.assertIn('50',result[0]['chinese'])


if __name__=='__main__':unittest.main()
