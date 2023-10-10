from fastapi import APIRouter,Path,HTTPException,Header,Depends,Body,Query
from pydantic import BaseModel
from typing import Optional, Dict,Any
from lib.database import dbconn
from lib.jwtToken import check_jwt

router=APIRouter(prefix="/blog/comment",tags=["Blog Comment"])

@router.post("/add",dependencies=[Depends(check_jwt)])
async def comment_add(
  user_id: str = Body(...),
  article_id: int = Body(...),
  content: str = Body(...),
):
  conn=dbconn()
  cursor = conn.cursor()
  
  try:
    cursor.execute("SELECT id FROM sys_user WHERE userid = %s", (user_id,))
    userid = cursor.fetchone()
  
    cursor.execute("INSERT INTO blog_comment (article_id, user_id, content, createdate) VALUES (%s, %s, %s, NOW())", (article_id, userid[0],content))
    conn.commit()
    cursor.execute("UPDATE blog_article SET comment_count = comment_count + 1 WHERE id = %s", (article_id,))
    conn.commit()
    return {
      "success":True,
    }
  except Exception as e:
    conn.rollback()
    raise HTTPException(status_code=502, detail=str(e))
  finally:
    cursor.close()
    conn.close()
  





@router.put("/edit",dependencies=[Depends(check_jwt)])
async def comment_edit(
  id: int = Body(...),
  user_id: str = Body(...),
  article_id: int = Body(...),
  content: str = Body(...),
):
  
  conn = dbconn()
  cursor = conn.cursor()
  try:
    cursor.execute("SELECT id FROM blog_comment WHERE id = %s", (id,))
    existing_id = cursor.fetchone()
    
    cursor.execute("SELECT id FROM sys_user WHERE userid = %s", (user_id,))
    userid = cursor.fetchone()

    if not existing_id:
      return {
        "success":False,
        "message":f"Menu with ID {id} not found"
      }
    cursor.execute("UPDATE blog_comment SET user_id = %s, article_id = %s, content = %s, updated = NOW() WHERE id = %s", (
      userid[0],article_id,content, id))
    conn.commit()
    return {
      "success":True,
    }
  except Exception as e:
    conn.rollback()
    raise HTTPException(status_code=502, detail=str(e))
  finally:
    cursor.close()
    conn.close()




@router.get("/list",dependencies=[Depends(check_jwt)])
async def comment_list(
    user_id: Optional[int] = Query(None),
    article_id: Optional[int] = Query(None),
    query: Optional[str] = Query(None),
    page: int = Query(1, description="页码，从1开始"),
    pageSize: int = Query(10, description="每页记录数")
) -> Dict[str, Any]:
  try:
    conn = dbconn()
    cursor = conn.cursor()

    sql = """
        SELECT * FROM blog_comment
        WHERE (%s IS NULL OR user_id = %s)
        AND (%s IS NULL OR article_id = %s)
        AND (%s IS NULL OR ( content LIKE %s))
        LIMIT %s OFFSET %s
    """
    params = [user_id, user_id, article_id, article_id, query, f"%{query}%", pageSize, (page - 1) * pageSize]

    count_sql = """
        SELECT COUNT(*) FROM blog_comment
        WHERE (%s IS NULL OR user_id = %s)
        AND (%s IS NULL OR article_id = %s)
        AND (%s IS NULL OR (content LIKE %s))
    """
    params_count = [user_id, user_id, article_id, article_id, query, f"%{query}%"]
    
    cursor.execute(count_sql, params_count)
    total_records = cursor.fetchone()[0]

    cursor.execute(sql, params)
    result = [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]

    user_ids = {row["user_id"] for row in result if "user_id" in row}
    if user_ids:
      author_sql = "SELECT id, userid FROM sys_user WHERE id IN %s"
      cursor.execute(author_sql, (tuple(user_ids),))
      user_data = cursor.fetchall()
      
      user_id_to_userid = {row[0]: row[1] for row in user_data}

      for row in result:
        if "user_id" in row:
          userID = row["user_id"]
          if userID in user_id_to_userid:
            row["user_name"] = user_id_to_userid[userID]

    total_pages = (total_records + pageSize - 1) // pageSize

    return {
      "success":True,
      "data": result,
      "totalRecords": total_records,
      "totalPages": total_pages,
      "currentPage": page,
      "pageSize": pageSize
    }

  except Exception as e:
    conn.rollback()
    raise HTTPException(status_code=500, detail=str(e))
  finally:
    cursor.close()
    conn.close()


@router.delete("/delete",dependencies=[Depends(check_jwt)])
async def comment_delete(id: int):
  conn = dbconn()
  cursor = conn.cursor()

  try:
    cursor.execute("SELECT * FROM blog_comment WHERE id = %s", (id,))
    existing_data = cursor.fetchone()
    print(existing_data,existing_data[2])
    if not existing_data:
      return {
        "success":False,
        "message":f"User with ID {id} not found"
      }
    cursor.execute("DELETE FROM blog_comment WHERE id = %s", (existing_data[0],))
    conn.commit()
    cursor.execute("UPDATE blog_article SET comment_count = comment_count - 1 WHERE id = %s", (existing_data[3],))
    conn.commit()
    return {
      "success":True,
    }
  except Exception as e:
    conn.rollback()
    raise HTTPException(status_code=502, detail=str(e))
  finally:
    cursor.close()
    conn.close()