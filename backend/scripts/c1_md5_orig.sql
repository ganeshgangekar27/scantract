SELECT md5(string_agg(id::text||coalesce(explanation,'')||coalesce(formatted_citation,''),'|' ORDER BY id)) FROM risk_findings WHERE contract_id=1;
