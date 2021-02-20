import React from 'react';
import { shallow } from 'enzyme';
import Question from '../question';


const questions = [
  {
    "tag": "cde",
    "cde": "EDUCATION",
    "datatype": "range",
    "instructions": "",
    "title": "What was the highest level of schooling you completed",
    "survey_question_instruction": "To date",
    "copyright_text": "",
    "source": "",
    "spec": {
      "ui": "range",
      "options": [
        {
          "code": "0",
          "text": "None"
        },
        {
          "code": "1",
          "text": "Primary"
        },
        {
          "code": "2",
          "text": "Secondary"
        },
        {
          "code": "3",
          "text": "Tertiary"
        }
      ]
    }
  }
];

describe('given Question component that receives questions as prop', () => {
  describe('with questions', () => {
    let wrapper;
    beforeAll(() => {
      wrapper = shallow(<Question questions={questions} />);
    });
    it('renders without crashing', () => {
      expect(wrapper)
    });
  });
});

//it('renders without crashing', () => {
//  shallow(<Question />);
//});

