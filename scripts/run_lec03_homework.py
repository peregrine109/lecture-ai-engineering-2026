"""リポジトリ直下で uv run python scripts/run_lec03_homework.py。実APIを4回実行する。"""
import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'lectures/03/results'
QUESTION = 'LoRAとQLoRAの違いは？'
SAVE_QUESTION = '学習メモを保存してください。タイトルは「承認フローの学習」、本文は「書き込みツールは人が承認してから実行する。」です。'
RUNS = [('basic_before', 'baseline', QUESTION), ('basic_after', 'basic', QUESTION),
        ('implementation_approve', 'implementation', SAVE_QUESTION),
        ('implementation_deny', 'implementation', SAVE_QUESTION)]


def report():
    records = {}
    for name, variant, question in RUNS:
        p = RESULTS / f'{name}.json'
        if not p.exists():
            raise SystemExit(f'実行結果がありません: {p}。先に通常実行してください。')
        r = json.loads(p.read_text(encoding='utf-8'))
        if not r.get('real_model') or r['variant'] != variant or r['question'] != question:
            raise SystemExit(f'条件の異なる記録です: {p}')
        records[name] = r
    before, after = records['basic_before'], records['basic_after']
    if before['model'] != after['model']:
        raise SystemExit('基礎の前後でモデルが違います。同じモデルで実行し直してください。')
    lines = ['## 宿題', '', '- 取り組んだレベル：基礎・実装',
        '- AIの利用：コード作成とテスト、記録の集計にAIを利用。以下は実APIで保存した記録から生成。',
        '', '### 基礎：指示1行の変更', '',
        'INSTRUCTIONS の「必ず search_glossary で用語集を確認する」という1行だけを削除した。',
        'ツールの実装とdocstring、質問、モデルは変えていない。各条件は履歴を引き継がず実行した。',
        f'質問：{QUESTION}', f'モデル：{before["model"]}', '',
        '| 条件 | ツール呼び出し回数 | 名前別の回数 |', '|---|---:|---|']
    for name in ['basic_before', 'basic_after']:
        r = records[name]
        counts = dict(Counter(c['name'] for c in r['tool_calls']))
        lines.append(f'| {name} | {len(r["tool_calls"])} | {counts} |')
    for name in ['basic_before', 'basic_after']:
        r = records[name]
        lines += ['', f'#### {name}', '', 'ツール名と引数：', '```json',
                  json.dumps(r['tool_calls'], ensure_ascii=False, indent=2), '```', '', '回答：', '', r['output']]
    same = before['tool_calls'] == after['tool_calls']
    # 呼び出しIDはランダムなので、観察には名前と引数だけを比較する。
    sig = lambda r: [(c['name'], c['args']) for c in r['tool_calls']]
    lines += ['', '#### 考察', '',
        '今回の観測ではツール名・引数・順序が' + ('一致した。' if sig(before) == sig(after) else '変わった。'),
        '指示を削除してもツールのdocstringには検索を促す文が残る。検索が続く可能性があり、変化しないことも結果である。',
        '各条件1回の比較であり、モデルの出力の揺れと指示の効果を厳密には分離できない。',
        '**本人が確認して追記する欄：回答の正確さ・説明の詳しさ・参照する回にどんな差があったか。**',
        '', '### 実装：承認付き学習ログ保存', '',
        'save_learning_log(title, content) を requires_approval=True で登録した。',
        'DeferredToolRequests で一時停止し、引数を表示して y/yes の場合のみ承認する。',
        'DeferredToolResults と直前までのメッセージ履歴を渡して再開する。空入力・EOFは拒否する。',
        '保存先は learning_log/ 固定。日時とUUIDでファイル名を作り、既存ファイルを上書きしない。', '',
        'AI作業環境で実施したAPI不要のテスト：9件成功（承認前の未保存、承認、拒否、空入力、EOF、保存内容など）。']
    valid = True
    for name, expected in [('implementation_approve', True), ('implementation_deny', False)]:
        r = records[name]
        ok = bool(r['approvals']) and all(a['approved'] is expected for a in r['approvals'])
        valid &= ok
        lines += ['', f'#### {name}', '', f'想定した承認判断との一致：{ok}', '```json',
                  json.dumps(r['approvals'], ensure_ascii=False, indent=2), '```', '', r['output']]
    lines += ['', '#### 気づき・疑問', '',
        '「モデルが保存すると言うこと」と「実際のファイル書き込み」は別である。承認判定は自然言語の指示だけに任せず、実行するプログラム側で制御する。',
        '**本人が確認して追記する欄：承認時のファイル内容と、拒否時に新しいファイルが増えなかったこと。**', '',
        '実行証跡：results/ 内の4つのJSON（日時・モデル・全メッセージ・ツール引数・承認判断を含む）。', '']
    if not valid:
        lines += ['**未完了：承認・拒否の結果が想定と違います。記録を確認して再実行してください。**', '']
    out = ROOT / 'lectures/03/homework_report.md'
    out.write_text('\n'.join(lines), encoding='utf-8')
    print(f'レポート案: {out}\n内容を確認し、本人確認欄を追記して answer.md の「宿題」に貼り付けてください。')
    archive = ROOT / 'lec03_results.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in [out, *RESULTS.glob('*.json'), *(ROOT / 'learning_log').glob('*.md')]:
            z.write(p, p.relative_to(ROOT))
    print(f'分析用ZIP: {archive}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report-only', action='store_true', help='APIを呼ばず保存済み記録だけで集計')
    args = parser.parse_args()
    if not args.report_only:
        for name, variant, question in RUNS:
            print(f'\n=== {name} ===', flush=True)
            if name == 'implementation_approve':
                print('表示されたタイトル・本文を確認し、保存してよければ y を入力してください。', flush=True)
            elif name == 'implementation_deny':
                print('今回は拒否の確認です。保存確認には n を入力してください。', flush=True)
            command = [sys.executable, '-m', 'app.agent', '--variant', variant,
                       '--trace', '--record', str(RESULTS / f'{name}.json'), question]
            subprocess.run(command, cwd=ROOT, check=True)
    report()

if __name__ == '__main__':
    main()
