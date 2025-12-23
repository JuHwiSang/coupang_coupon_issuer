#!/usr/bin/env python3
"""엑셀 예시 파일 생성 스크립트

사용법:
    uv run generate-examples
"""

from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment


def create_excel_with_headers():
    """헤더가 포함된 새 워크북 생성"""
    wb = Workbook()
    ws = wb.active
    
    # 헤더 정의 (7개 컬럼)
    headers = [
        '쿠폰이름',
        '쿠폰타입',
        '쿠폰유효기간',
        '할인방식',
        '할인금액/비율',
        '발급개수',
        '옵션ID'
    ]
    
    # 헤더 스타일 설정
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    
    # 헤더 작성
    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
    
    # 컬럼 너비 조절
    ws.column_dimensions['A'].width = 20  # 쿠폰이름
    ws.column_dimensions['B'].width = 15  # 쿠폰타입
    ws.column_dimensions['C'].width = 15  # 쿠폰유효기간
    ws.column_dimensions['D'].width = 20  # 할인방식
    ws.column_dimensions['E'].width = 15  # 할인금액/비율
    ws.column_dimensions['F'].width = 12  # 발급개수
    ws.column_dimensions['G'].width = 25  # 옵션ID
    
    return wb, ws


def generate_basic_example(output_dir: Path):
    """기본 예제 생성 - 간단한 쿠폰 2개"""
    wb, ws = create_excel_with_headers()
    
    # 데이터 행
    data = [
        ['즉시할인쿠폰', '즉시할인', 30, 'RATE', 10, '', '1234567890,1234567891'],
        ['다운로드쿠폰', '다운로드쿠폰', 15, 'PRICE', 1000, 100, '9876543210'],
    ]
    
    for row_idx, row_data in enumerate(data, start=2):
        for col_idx, value in enumerate(row_data, start=1):
            ws.cell(row=row_idx, column=col_idx, value=value)
    
    output_path = output_dir / 'basic.xlsx'
    wb.save(output_path)
    print(f"✓ 기본 예제 생성: {output_path}")


def generate_comprehensive_example(output_dir: Path):
    """포괄적 예제 - 모든 쿠폰 타입과 할인 방식 포함"""
    wb, ws = create_excel_with_headers()
    
    # 데이터 행 (모든 조합 예시)
    data = [
        # 즉시할인 쿠폰들
        ['즉시할인_정률할인', '즉시할인', 30, 'RATE', 15, '', '1111111111,2222222222,3333333333'],
        ['즉시할인_정액할인', '즉시할인', 60, 'PRICE', 5000, '', '4444444444,5555555555'],
        ['즉시할인_수량할인', '즉시할인', 45, 'FIXED_WITH_QUANTITY', 2, '', '6666666666'],
        
        # 다운로드 쿠폰들
        ['다운로드_정률할인', '다운로드쿠폰', 7, 'RATE', 20, 50, '7777777777,8888888888'],
        ['다운로드_정액할인', '다운로드쿠폰', 14, 'PRICE', 3000, 200, '9999999999'],
        ['다운로드_수량할인', '다운로드쿠폰', 30, 'FIXED_WITH_QUANTITY', 1, 150, '1010101010,2020202020'],
    ]
    
    for row_idx, row_data in enumerate(data, start=2):
        for col_idx, value in enumerate(row_data, start=1):
            ws.cell(row=row_idx, column=col_idx, value=value)
    
    output_path = output_dir / 'comprehensive.xlsx'
    wb.save(output_path)
    print(f"✓ 포괄적 예제 생성: {output_path}")


def generate_edge_cases_example(output_dir: Path):
    """엣지 케이스 예제 - 최소/최대값 테스트"""
    wb, ws = create_excel_with_headers()
    
    # 데이터 행 (엣지 케이스)
    data = [
        # 정률할인 최소/최대
        ['정률할인_최소1%', '즉시할인', 1, 'RATE', 1, '', '1234567890'],
        ['정률할인_최대99%', '다운로드쿠폰', 365, 'RATE', 99, 1000, '1234567891'],
        
        # 정액할인 최소
        ['정액할인_최소10원', '다운로드쿠폰', 7, 'PRICE', 10, 50, '1234567892'],
        ['정액할인_큰금액', '즉시할인', 90, 'PRICE', 50000, '', '1234567893,1234567894'],
        
        # 수량할인 최소
        ['수량할인_최소1개', '다운로드쿠폰', 30, 'FIXED_WITH_QUANTITY', 1, 100, '1234567895'],
        
        # 여러 옵션ID (최대 100개까지 테스트 - 다운로드쿠폰 제한)
        ['다운로드_다중옵션', '다운로드쿠폰', 30, 'PRICE', 2000, 300, 
         ','.join([str(i) for i in range(1000000000, 1000000010)])],  # 10개 옵션
         
        # 즉시할인 다중 옵션 (더 많이 가능)
        ['즉시할인_다중옵션', '즉시할인', 30, 'RATE', 10, '',
         ','.join([str(i) for i in range(2000000000, 2000000050)])],  # 50개 옵션
    ]
    
    for row_idx, row_data in enumerate(data, start=2):
        for col_idx, value in enumerate(row_data, start=1):
            ws.cell(row=row_idx, column=col_idx, value=value)
    
    output_path = output_dir / 'edge_cases.xlsx'
    wb.save(output_path)
    print(f"✓ 엣지 케이스 예제 생성: {output_path}")


def main():
    """메인 함수"""
    # 프로젝트 루트 디렉토리 기준으로 examples 디렉토리 생성
    project_root = Path(__file__).parent.parent
    output_dir = project_root / 'examples'
    output_dir.mkdir(exist_ok=True)
    
    print(f"\n엑셀 예시 파일 생성 중... (출력 디렉토리: {output_dir})\n")
    
    # 예제 파일들 생성
    generate_basic_example(output_dir)
    generate_comprehensive_example(output_dir)
    generate_edge_cases_example(output_dir)
    
    print(f"\n✅ 완료! 3개의 예제 파일이 생성되었습니다.")
    print(f"\n검증 명령어:")
    print(f"  uv run python main.py verify examples/")
    print()


if __name__ == '__main__':
    main()
