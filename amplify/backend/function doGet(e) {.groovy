function doGet(e) {
  const action = e.parameter.action;
  const startDate = e.parameter.startDate;
  const endDate = e.parameter.endDate;

  if (action === "getEvents") {
    return getCalendarEvents(startDate, endDate);
  }
}

function doPost(e) {
  const params = JSON.parse(e.postData.contents);

  if (params.action === "addEvent") {
    return addCalendarEvent(params.Date, params.Hours, params.Title);
  } else if (params.action === "deleteEvent") {
    return deleteCalendarEvent(params.Date, params.Time, params.Title);
  } else if (params.action === "sendEmail") {
    return sendEmail(params.Subject, params.Body, params.To);
  }
}

function getCalendarEvents(startDate, endDate) {
  const calendar = CalendarApp.getDefaultCalendar();
  const events = calendar.getEvents(new Date(startDate), new Date(endDate));
  const result = events.map(event => ({
    id: event.getId(),
    title: event.getTitle(),
    startTime: event.getStartTime(),
    endTime: event.getEndTime()
  }));
  return ContentService.createTextOutput(JSON.stringify(result)).setMimeType(ContentService.MimeType.JSON);
}

function addCalendarEvent(date, hours, title) {
  const calendar = CalendarApp.getDefaultCalendar();
  const startTime = new Date(date);
  const endTime = new Date(startTime.getTime() + hours * 60 * 60 * 1000);
  const event = calendar.createEvent(title, startTime, endTime);

  const result = {
    id: event.getId(),
    title: event.getTitle(),
    startTime: event.getStartTime(),
    endTime: event.getEndTime()
  };
  return ContentService.createTextOutput(JSON.stringify(result)).setMimeType(ContentService.MimeType.JSON);
}


function deleteEventByDateAndTitle(date, time, title) {
  try {
    const calendar = CalendarApp.getDefaultCalendar();
    if (!calendar) {
      throw new Error("Default calendar not found.");
    }

    // イベントの開始時刻を生成
    const startTime = new Date(`${date}T${time}:00`);
    const endTime = new Date(startTime);
    endTime.setHours(23, 59, 59); // 同日の終了時刻を設定

    // 指定範囲内のイベントを取得
    const events = calendar.getEvents(startTime, endTime);
    let deletedCount = 0;

    for (const event of events) {
      // タイトルと開始時刻が一致するイベントを削除
      if (event.getTitle() === title && event.getStartTime().getTime() === startTime.getTime()) {
        event.deleteEvent();
        deletedCount++;
      }
    }

    // 削除結果を返却
    return ContentService.createTextOutput(JSON.stringify({
      success: true,
      message: `${deletedCount} event(s) deleted.`,
    })).setMimeType(ContentService.MimeType.JSON);
  } catch (error) {
    // エラーメッセージを返却
    return ContentService.createTextOutput(JSON.stringify({
      success: false,
      message: error.message,
    })).setMimeType(ContentService.MimeType.JSON);
  }
}
  
  

function sendEmail(subject, body, to) {
  GmailApp.sendEmail(to, subject, body);
  return ContentService.createTextOutput("Email sent").setMimeType(ContentService.MimeType.TEXT);
}
