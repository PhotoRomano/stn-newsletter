// Deploy as Web App (Execute as: Me, Who has access: Anyone).
// The resulting /exec URL is what all sign-up forms POST to.

const SHEET_ID = '1wAKlKyWzOQsbK4DU6BzvvGuWeBnnfdjWFtqM_ITE5jk';
const NOTIFY_EMAIL = 'stnicholas.soc@gmail.com';

function getOrCreateSheet(name, headerRow) {
  var ss = SpreadsheetApp.openById(SHEET_ID);
  var sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
    sheet.appendRow(headerRow);
  }
  return sheet;
}

function doPost(e) {
  var p = e.parameter;
  var form = p['_form'] || 'Unknown';

  if (form === 'SerbFest Volunteer') {
    var row = [
      new Date(),
      p['First Name'] || '',
      p['Last Name'] || '',
      p['Email'] || '',
      p['Phone'] || '',
      p['Friday Setup'] || '',
      p['Saturday'] || '',
      p['Sunday'] || '',
      p['Kitchen Prep & Cooking'] || '',
      p['Grill/Roasting'] || '',
      p['Tent Setup/Breakdown'] || '',
      p['Serving/Cashier'] || '',
      p['Cleaning'] || '',
      p['Kids Zone Supervision'] || '',
      p['Yard/Grounds Work'] || '',
      p['Wherever Needed'] || '',
      p['Notes'] || ''
    ];
    getOrCreateSheet('SerbFest Volunteers', [
      'Timestamp', 'First Name', 'Last Name', 'Email', 'Phone',
      'Friday Setup', 'Saturday', 'Sunday',
      'Kitchen Prep & Cooking', 'Grill/Roasting', 'Tent Setup/Breakdown',
      'Serving/Cashier', 'Cleaning', 'Kids Zone Supervision', 'Yard/Grounds Work',
      'Wherever Needed', 'Notes'
    ]).appendRow(row);
    notify(form, row[1] + ' ' + row[2], row);
    return ContentService.createTextOutput(JSON.stringify({ ok: true }))
      .setMimeType(ContentService.MimeType.JSON);
  }

  if (form === 'Cookie and Cake') {
    var row = [
      new Date(),
      p['First Name'] || '',
      p['Last Name'] || '',
      p['Email'] || '',
      p['Phone'] || '',
      p['Baking What'] || '',
      p['Baking Drop-off'] || '',
      p['Staffing Shift'] || '',
      p['Notes'] || ''
    ];
    getOrCreateSheet('Cookie and Cake Sign-Ups', [
      'Timestamp', 'First Name', 'Last Name', 'Email', 'Phone',
      'Baking - What/How Much', 'Baking - Drop-off', 'Staffing - Shift', 'Notes'
    ]).appendRow(row);
    notify(form, row[1] + ' ' + row[2], row);
    return ContentService.createTextOutput(JSON.stringify({ ok: true }))
      .setMimeType(ContentService.MimeType.JSON);
  }

  var isYoungAdults = form === 'Young Adults';

  var row = [
    new Date(),
    form,
    isYoungAdults ? p['Teen First Name'] : p['Student First Name'],
    isYoungAdults ? p['Teen Last Name'] : p['Student Last Name'],
    isYoungAdults ? p['Teen Age'] : p['Student Age'],
    p['Grade'] || '',
    p['Parent First Name'] || '',
    p['Parent Last Name'] || '',
    p['Parent Email'] || '',
    p['Parent Phone'] || '',
    p['Teen Contact'] || '',
    p['Interested in Leading'] || '',
    p['Activity or Volunteer Idea'] || '',
    p['Siblings'] || '',
    p['Notes'] || '',
    p['Serbian Level'] || ''
  ];

  var sheet = SpreadsheetApp.openById(SHEET_ID).getSheets()[0];
  sheet.appendRow(row);
  notify(form, row[2] + ' ' + row[3], row);

  return ContentService.createTextOutput(JSON.stringify({ ok: true }))
    .setMimeType(ContentService.MimeType.JSON);
}

function notify(form, name, row) {
  try {
    MailApp.sendEmail({
      to: NOTIFY_EMAIL,
      subject: form + ' Sign-Up: ' + name,
      body: 'New sign-up received:\n\n' + row.join('\n')
    });
  } catch (err) {
    // don't fail the request just because the notification email hiccuped
  }
}
