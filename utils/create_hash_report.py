import pandas as pd
import os

def create_hash_report(collected_data, report_file):
    try:
        # 수집된 데이터를 DataFrame으로 변환
        new_df = pd.DataFrame(collected_data)

        # 엑셀 파일이 이미 존재하는지 확인
        if os.path.exists(report_file):
            # 기존 엑셀 파일 읽기
            existing_df = pd.read_excel(report_file)
            # 기존 데이터와 새로운 데이터를 병합
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            # 엑셀 파일이 없으면 새로운 데이터만 사용
            combined_df = new_df
        # DataFrame을 엑셀 파일로 저장
        combined_df.to_excel(report_file, index=False)
    except Exception:
        pass
