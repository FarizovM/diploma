def getNearesPost(lat,len):
    if not lat or not len:
        return {"error": "Missing parameters lat or len"}
    
    try:
        lat = float(lat)
        len = float(len)

        return {lat,len}
    except (ValueError) as e:
        return {"error": e, "status": 500}
    
