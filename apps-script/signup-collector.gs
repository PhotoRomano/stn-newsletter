// Deploy as Web App (Execute as: Me, Who has access: Anyone).
// The resulting /exec URL is what the 3 sign-up forms POST to.

const SHEET_ID = '1wAKlKyWzOQsbK4DU6BzvvGuWeBnnfdjWFtqM_ITE5jk';
const NOTIFY_EMAIL = 'stnicholas.soc@gmail.com';

function doPost(e) {
  var p = e.parameter;
  var form = p['_form'] || 'Unknown';
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
    p['Notes'] || ''
  ];

  var sheet = SpreadsheetApp.openById(SHEET_ID).getSheets()[0];
  sheet.appendRow(row);

  try {
    MailApp.sendEmail({
      to: NOTIFY_EMAIL,
      subject: form + ' Sign-Up: ' + row[2] + ' ' + row[3],
      body: 'New sign-up received:\n\n' + row.join('\n')
    });
  } catch (err) {
    // don't fail the request just because the notification email hiccuped
  }

  return ContentService.createTextOutput(JSON.stringify({ ok: true }))
    .setMimeType(ContentService.MimeType.JSON);
}
